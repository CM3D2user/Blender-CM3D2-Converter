import bpy, bmesh, mathutils
import os, re, struct, time, math
from operator import itemgetter
from . import common



# メインオペレーター
class export_cm3d2_model(bpy.types.Operator):
	bl_idname = 'export_mesh.export_cm3d2_model'
	bl_label = "CM3D2モデル (.model)"
	bl_description = "カスタムメイド3D2のmodelファイルを書き出します"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".model"
	filter_glob = bpy.props.StringProperty(default="*.model", options={'HIDDEN'})
	
	scale = bpy.props.FloatProperty(name="倍率", default=0.2, min=0.01, max=100, soft_min=0.01, soft_max=100, step=10, precision=2, description="エクスポート時のメッシュ等の拡大率です")
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.EnumProperty(
		name="ファイルバージョン",
		items=[
			('2001', '2001', 'model version 2001 (available only for com3d2)', 'NONE', 0),
			('2000', '2000', 'model version 2000 (com3d2 version)', 'NONE', 1),
			('1000', '1000', 'model version 1000 (available for cm3d2/com3d2)', 'NONE', 2),
		], default='1000')
	model_name = bpy.props.StringProperty(name="model名", default="*")
	base_bone_name = bpy.props.StringProperty(name="基点ボーン名", default="*")
	
	items = [
		('ARMATURE', "アーマチュア", "", 'OUTLINER_OB_ARMATURE', 1),
		('TEXT', "テキスト", "", 'FILE_TEXT', 2),
		('OBJECT_PROPERTY', "オブジェクト内プロパティ", "", 'OBJECT_DATAMODE', 3),
		('ARMATURE_PROPERTY', "アーマチュア内プロパティ", "", 'ARMATURE_DATA', 4),
		]
	bone_info_mode = bpy.props.EnumProperty(items=items, name="ボーン情報元", default='OBJECT_PROPERTY', description="modelファイルに必要なボーン情報をどこから引っ張ってくるか選びます")
	
	items = [
		('TEXT', "テキスト", "", 'FILE_TEXT', 1),
		('MATERIAL', "マテリアル", "", 'MATERIAL', 2),
		]
	mate_info_mode = bpy.props.EnumProperty(items=items, name="マテリアル情報元", default='MATERIAL', description="modelファイルに必要なマテリアル情報をどこから引っ張ってくるか選びます")
	
	is_arrange_name = bpy.props.BoolProperty(name="データ名の連番を削除", default=True, description="「○○.001」のような連番が付属したデータ名からこれらを削除します")
	
	is_convert_tris = bpy.props.BoolProperty(name="四角面を三角面に", default=True, description="四角ポリゴンを三角ポリゴンに変換してから出力します、元のメッシュには影響ありません")
	is_normalize_weight = bpy.props.BoolProperty(name="ウェイトの合計を1.0に", default=True, description="4つのウェイトの合計値が1.0になるように正規化します")
	is_convert_bone_weight_names = bpy.props.BoolProperty(name="頂点グループ名をCM3D2用に変換", default=True, description="全ての頂点グループ名をCM3D2で使える名前にしてからエクスポートします")
	is_apply_modifiers = bpy.props.BoolProperty(name="モディファイアを適用", default=False)
	
	is_batch = bpy.props.BoolProperty(name="バッチモード", default=False, description="モードの切替やエラー個所の選択を行いません")
	export_tangent = bpy.props.BoolProperty(name="接空間情報出力", default=False, description="接空間情報(binormals, tangents)を出力する")
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return True
		return False
	
	def report_cancel(self, report_message, report_type={'ERROR'}, resobj={'CANCELLED'}):
		"""エラーメッセージを出力してキャンセルオブジェクトを返す"""
		self.report(type=report_type, message=report_message)
		return resobj
	

	def precheck(self, context):
		"""データの成否チェック"""
		ob = context.active_object
		if not ob:
			return self.report_cancel("アクティブオブジェクトがありません")
		if ob.type != 'MESH':
			return self.report_cancel("メッシュオブジェクトを選択した状態で実行してください")
		if not len(ob.material_slots):
			return self.report_cancel("マテリアルがありません")
		for slot in ob.material_slots:
			if not slot.material:
				return self.report_cancel("空のマテリアルスロットを削除してください")
			try:
				slot.material['shader1']
				slot.material['shader2']
			except:
				return self.report_cancel("マテリアルに「shader1」と「shader2」という名前のカスタムプロパティを用意してください")
		me = ob.data
		if not me.uv_layers.active:
			return self.report_cancel("UVがありません")
		if 65535 < len(me.vertices):
			return self.report_cancel("エクスポート可能な頂点数を大幅に超えています、最低でも65535未満には削減してください")
		return None
	

	def invoke(self, context, event):
		res = self.precheck(context)
		if res: return res
		ob = context.active_object
		
		# model名とか
		ob_names = common.remove_serial_number(ob.name, self.is_arrange_name).split('.')
		self.model_name = ob_names[0]
		self.base_bone_name = ob_names[1] if 2 <= len(ob_names) else 'Auto'
		
		# ボーン情報元のデフォルトオプションを取得
		if "BoneData" in context.blend_data.texts:
			if "LocalBoneData" in context.blend_data.texts:
				self.bone_info_mode = 'TEXT'
		if "BoneData:0" in ob:
			ver = ob.get("ModelVersion")
			if ver and ver >= 1000:
				self.version = str(ver)
			if "LocalBoneData:0" in ob:
				self.bone_info_mode = 'OBJECT_PROPERTY'
		arm_ob = ob.parent
		if arm_ob:
			if arm_ob.type == 'ARMATURE':
				self.bone_info_mode = 'ARMATURE_PROPERTY'
		else:
			for mod in ob.modifiers:
				if mod.type == 'ARMATURE':
					if mod.object:
						self.bone_info_mode = 'ARMATURE_PROPERTY'
						break
		
		# エクスポート時のデフォルトパスを取得
		if common.preferences().model_default_path:
			self.filepath = common.default_cm3d2_dir(common.preferences().model_default_path, self.model_name, "model")
		else:
			self.filepath = common.default_cm3d2_dir(common.preferences().model_export_path, self.model_name, "model")
		
		# バックアップ関係
		self.is_backup = bool(common.preferences().backup_ext)
		
		self.scale = 1.0 / common.preferences().scale
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}


	# 'is_batch' がオンなら非表示
	def draw(self, context):
		self.layout.prop(self, 'scale')
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not common.preferences().backup_ext:
			row.enabled = False
		self.layout.prop(self, 'is_arrange_name', icon='SAVE_AS')
		box = self.layout.box()
		box.prop(self, 'version', icon='LINENUMBERS_ON')
		box.prop(self, 'model_name', icon='SORTALPHA')
		
		row = box.row()
		row.prop(self, 'base_bone_name', icon='CONSTRAINT_BONE')
		if self.base_bone_name == 'Auto':
			row.enabled = False
		
		prefs = common.preferences()
		box = self.layout.box()
		col = box.column(align=True)
		col.label(text="ボーン情報元", icon='BONE_DATA')
		col.prop(self, 'bone_info_mode', icon='BONE_DATA', expand=True)
		col = box.column(align=True)
		col.label(text="マテリアル情報元", icon='MATERIAL')
		col.prop(self, 'mate_info_mode', icon='MATERIAL', expand=True)
		box = self.layout.box()
		box.label("メッシュオプション")
		box.prop(self, 'is_convert_tris', icon='MESH_DATA')
		box.prop(prefs, 'skip_shapekey', icon='SHAPEKEY_DATA')
		box.prop(self, 'export_tangent', icon='CURVE_BEZCIRCLE')
		sub_box = box.box()
		sub_box.prop(self, 'is_normalize_weight', icon='MOD_VERTEX_WEIGHT')
		sub_box.prop(self, 'is_convert_bone_weight_names', icon_value=common.preview_collections['main']['KISS'].icon_id)
		sub_box = box.box()
		sub_box.prop(self, 'is_apply_modifiers', icon='MODIFIER')
		row = sub_box.row()
		row.prop(prefs, 'custom_normal_blend', icon='SNAP_NORMAL', slider=True)
		row.enabled = self.is_apply_modifiers

	def copy_and_activate_ob(self, context, ob):
		new_ob = ob.copy()
		new_me = ob.data.copy()
		new_ob.data = new_me
		context.scene.objects.link(new_ob)
		context.scene.objects.active = new_ob
		new_ob.select = True
		return new_ob

	def execute(self, context):
		start_time = time.time()

		selected_layers = bpy.context.scene.layers[:]
		bpy.context.scene.layers = (True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True)
		selected_objs = context.selected_objects
		source_objs = []
		selected_count = 0
		prev_mode = None
		selected_meshes = []
		try:
			ob_source = context.active_object
			ob_main = None
			if self.is_batch:
				# アクティブオブジェクトを１つコピーするだけでjoinしない
				source_objs.append(ob_source)
				ob_source.select = False
				self.copy_and_activate_ob(context, ob_source)

				if self.is_apply_modifiers:
					bpy.ops.object.forced_modifier_apply(is_applies=[True for i in range(32)])
			else:
				# 選択されたMESHオブジェクトをコピーしてjoin
				# 必要に応じて、モディファイアの強制適用を行う
				for selected in selected_objs:
					source_objs.append(selected)

					selected.select = False
					if selected.type == 'MESH':
						selected_meshes.append(selected)
						ob_created = self.copy_and_activate_ob(context, selected)
						if selected == ob_source:
							ob_main = ob_created
						if self.is_apply_modifiers:
							bpy.ops.object.forced_modifier_apply(is_applies=[True for i in range(32)])
						
						selected_count += 1

				mode = context.active_object.mode
				if mode != 'OBJECT':
					prev_mode = mode
					bpy.ops.object.mode_set(mode='OBJECT')

				if selected_count > 1:
					if ob_main:
						context.scene.objects.active = ob_main
					bpy.ops.object.join()
					self.report(type={'INFO'}, message="%d個のオブジェクトをマージしました" % selected_count)

			ob_copied = context.active_object
			ret = self.export(context, ob_copied,selected_meshes)
			if 'FINISHED' not in ret:
				return ret

			context.window_manager.progress_update(10)
			diff_time = time.time() - start_time
			self.report(type={'INFO'}, message="modelのエクスポートが完了しました。%.2f 秒 file=%s" % (diff_time, self.filepath))
			return ret
		finally:
			# 作業データの破棄（コピーデータを削除、選択状態の復元、アクティブオブジェクト、モードの復元）
			if ob_copied:
				me_copied = ob_copied.data
				context.blend_data.objects.remove(ob_copied, do_unlink=True)
				context.blend_data.meshes.remove(me_copied, do_unlink=True)

			for obj in source_objs:
				obj.select = True
				context.scene.objects.active = obj
			if ob_source:
				context.scene.objects.active = ob_source

			if prev_mode:
				bpy.ops.object.mode_set(mode=prev_mode)
			bpy.context.scene.layers = selected_layers
			
		
	def export(self, context, ob, selected_meshes):
		"""モデルファイルを出力"""
		prefs = common.preferences()

		if not self.is_batch:
			prefs.model_export_path = self.filepath
			prefs.scale = 1.0 / self.scale

		context.window_manager.progress_begin(0, 10)
		context.window_manager.progress_update(0)

		res = self.precheck(context)
		if res: return res
		me = ob.data

		if ob.active_shape_key_index != 0:
			ob.active_shape_key_index = 0
			me.update()

		# データの成否チェック
		if self.bone_info_mode == 'ARMATURE':
			arm_ob = ob.parent
			if arm_ob and arm_ob.type != 'ARMATURE':
				return self.report_cancel("メッシュオブジェクトの親がアーマチュアではありません")
			if not arm_ob:
				try:
					arm_ob = next(mod for mod in ob.modifiers if mod.type == 'ARMATURE' and mod.object)
				except StopIteration:
					return self.report_cancel("アーマチュアが見つかりません、親にするかモディファイアにして下さい")
				arm_ob = arm_ob.object
		elif self.bone_info_mode == 'TEXT':
			if "BoneData" not in context.blend_data.texts:
				return self.report_cancel("テキスト「BoneData」が見つかりません、中止します")
			if "LocalBoneData" not in context.blend_data.texts:
				return self.report_cancel("テキスト「LocalBoneData」が見つかりません、中止します")
		elif self.bone_info_mode == 'OBJECT_PROPERTY':
			if "BoneData:0" not in ob:
				return self.report_cancel("オブジェクトのカスタムプロパティにボーン情報がありません")
			if "LocalBoneData:0" not in ob:
				return self.report_cancel("オブジェクトのカスタムプロパティにボーン情報がありません")
		elif self.bone_info_mode == 'ARMATURE_PROPERTY':
			arm_ob = ob.parent
			if arm_ob and arm_ob.type != 'ARMATURE':
				return self.report_cancel("メッシュオブジェクトの親がアーマチュアではありません")
			if not arm_ob:
				try:
					arm_ob = next(mod for mod in ob.modifiers if mod.type == 'ARMATURE' and mod.object)
				except StopIteration:
					return self.report_cancel("アーマチュアが見つかりません、親にするかモディファイアにして下さい")
				arm_ob = arm_ob.object
			if "BoneData:0" not in arm_ob.data:
				return self.report_cancel("アーマチュアのカスタムプロパティにボーン情報がありません")
			if "LocalBoneData:0" not in arm_ob.data:
				return self.report_cancel("アーマチュアのカスタムプロパティにボーン情報がありません")
		else:
			return self.report_cancel("ボーン情報元のモードがおかしいです")
		
		if self.mate_info_mode == 'TEXT':
			for index, slot in enumerate(ob.material_slots):
				if "Material:" + str(index) not in context.blend_data.texts:
					return self.report_cancel("マテリアル情報元のテキストが足りません")
		context.window_manager.progress_update(1)
		
		# model名とか
		ob_names = common.remove_serial_number(ob.name, self.is_arrange_name).split('.')
		if self.model_name == '*':
			self.model_name = ob_names[0]
		if self.base_bone_name == '*':
			self.base_bone_name = ob_names[1] if 2 <= len(ob_names) else 'Auto'
		
		# BoneData情報読み込み
		base_bone_candidate = None
		bone_data = []
		if self.bone_info_mode == 'ARMATURE':
			bone_data = self.armature_bone_data_parser(arm_ob)
			base_bone_candidate = arm_ob.data['BaseBone']
		elif self.bone_info_mode == 'TEXT':
			bone_data_text = context.blend_data.texts["BoneData"]
			if 'BaseBone' in bone_data_text:
				base_bone_candidate = bone_data_text['BaseBone']
			bone_data = self.bone_data_parser(l.body for l in bone_data_text.lines)
		elif self.bone_info_mode in ['OBJECT_PROPERTY', 'ARMATURE_PROPERTY']:
			target = ob if self.bone_info_mode == 'OBJECT_PROPERTY' else arm_ob.data
			if 'BaseBone' in target:
				base_bone_candidate = target['BaseBone']
			bone_data = self.bone_data_parser(self.indexed_data_generator(target, prefix='BoneData:'))
		if len(bone_data) <= 0:
			return self.report_cancel("テキスト「BoneData」に有効なデータがありません")
		
		if self.base_bone_name not in (b['name'] for b in bone_data):
			if base_bone_candidate and self.base_bone_name == 'Auto':
				self.base_bone_name = base_bone_candidate
			else:
				return self.report_cancel("基点ボーンが存在しません")
		context.window_manager.progress_update(2)
		
		# LocalBoneData情報読み込み
		local_bone_data = []
		if self.bone_info_mode == 'ARMATURE':
			local_bone_data = self.armature_local_bone_data_parser(arm_ob)
		elif self.bone_info_mode == 'TEXT':
			local_bone_data_text = context.blend_data.texts["LocalBoneData"]
			local_bone_data = self.local_bone_data_parser(l.body for l in local_bone_data_text.lines)
		elif self.bone_info_mode in ['OBJECT_PROPERTY', 'ARMATURE_PROPERTY']:
			target = ob if self.bone_info_mode == 'OBJECT_PROPERTY' else arm_ob.data
			local_bone_data = self.local_bone_data_parser(self.indexed_data_generator(target, prefix='LocalBoneData:'))
		if len(local_bone_data) <= 0:
			return self.report_cancel("テキスト「LocalBoneData」に有効なデータがありません")
		local_bone_name_indices = {bone['name']:index for index, bone in enumerate(local_bone_data)}
		context.window_manager.progress_update(3)
		
		# ウェイト情報読み込み
		vertices = []
		is_over_one = 0
		is_under_one = 0
		for i, vert in enumerate(me.vertices):
			vgs = []
			for vg in vert.groups:
				name = common.encode_bone_name(ob.vertex_groups[vg.group].name, self.is_convert_bone_weight_names)
				index = local_bone_name_indices.get(name, -1)
				if 0 <= index and 0.0 < vg.weight:
					vgs.append([index, vg.weight])
			if len(vgs) == 0:
				if not self.is_batch:
					self.select_no_weight_vertices(context, local_bone_name_indices, selected_meshes)
				return self.report_cancel("ウェイトが割り当てられていない頂点が見つかりました、中止します")
			vgs = sorted(vgs, key=itemgetter(1), reverse=True)[0:4]
			total = sum(vg[1] for vg in vgs)
			if self.is_normalize_weight:
				for vg in vgs:
					vg[1] /= total
			else:
				if 1.01 < total:
					is_over_one += 1
				elif total < 0.99:
					is_under_one += 1
			if len(vgs) < 4:
				vgs += [(0, 0.0)] * (4 - len(vgs))
			vertices.append({
				'index': vert.index,
				'face_indexs': list(map(itemgetter(0), vgs)),
				'weights': list(map(itemgetter(1), vgs)),
				})
		if 1 <= is_over_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0を超えている頂点が見つかりました" % is_over_one)
		if 1 <= is_under_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0未満の頂点が見つかりました" % is_under_one)
		context.window_manager.progress_update(4)
			
		try:
			file = common.open_temporary(self.filepath, 'wb', is_backup=self.is_backup)
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可の可能性があります")
			return {'CANCELLED'}
		
		model_datas = {
			'bone_data': bone_data,
			'local_bone_data': local_bone_data,
			'vertices': vertices,
			}
		try:
			with file:
				self.write_model(context, file, **model_datas)
		except common.CM3D2ExportException as e:
			self.report(type={'ERROR'}, message=str(e))
			return {'CANCELLED'}

		return {'FINISHED'}

	def write_model(self, context, file, bone_data=[], local_bone_data=[], vertices=[]):
		"""モデルデータをファイルオブジェクトに書き込む"""
		ob = context.active_object
		me = ob.data
		prefs = common.preferences()
		
		# ファイル先頭
		common.write_str(file, 'CM3D2_MESH')
		self.version_num = int(self.version)
		file.write(struct.pack('<i', self.version_num))
		
		common.write_str(file, self.model_name)
		common.write_str(file, self.base_bone_name)
		
		# ボーン情報書き出し
		file.write(struct.pack('<i', len(bone_data)))
		for bone in bone_data:
			common.write_str(file, bone['name'])
			file.write(struct.pack('<b', bone['unknown']))
		context.window_manager.progress_update(3.3)
		for bone in bone_data:
			file.write(struct.pack('<i', bone['parent_index']))
		context.window_manager.progress_update(3.7)
		for bone in bone_data:
			file.write(struct.pack('<3f', bone['co'][0], bone['co'][1], bone['co'][2]))
			file.write(struct.pack('<4f', bone['rot'][1], bone['rot'][2], bone['rot'][3], bone['rot'][0]))
			if self.version_num >= 2001:
				use_scale = ('scale' in bone)
				file.write(struct.pack('<b', use_scale))
				if use_scale:
					bone_scale = bone['scale']
					file.write(struct.pack('<3f', bone_scale[0], bone_scale[1], bone_scale[2]))
		context.window_manager.progress_update(4)
		
		# 正しい頂点数などを取得
		bm = bmesh.new()
		bm.from_mesh(me)
		uv_lay = bm.loops.layers.uv.active
		vert_uvs = []
		vert_uvs_append = vert_uvs.append
		vert_iuv = {}
		vert_indices = {}
		vert_count = 0
		for vert in bm.verts:
			vert_uv = []
			vert_uvs_append(vert_uv)
			for loop in vert.link_loops:
				uv = loop[uv_lay].uv
				if uv not in vert_uv:
					vert_uv.append(uv)
					vert_iuv[hash((vert.index, uv.x, uv.y))] = vert_count
					vert_indices[vert.index] = vert_count
					vert_count += 1
		if 65535 < vert_count:
			raise common.CM3D2ExportException("頂点数がまだ多いです (現在%d頂点)。あと%d頂点以上減らしてください、中止します" % (vert_count, vert_count - 65535))
		context.window_manager.progress_update(5)
		
		file.write(struct.pack('<2i', vert_count, len(ob.material_slots)))
		
		# ローカルボーン情報を書き出し
		file.write(struct.pack('<i', len(local_bone_data)))
		for bone in local_bone_data:
			common.write_str(file, bone['name'])
		context.window_manager.progress_update(5.3)
		for bone in local_bone_data:
			for f in bone['matrix']:
				file.write(struct.pack('<f', f))
		context.window_manager.progress_update(5.7)
		
		# カスタム法線情報を取得
		if me.has_custom_normals:
			custom_normals = [mathutils.Vector() for i in range(len(me.vertices))]
			me.calc_normals_split()
			for loop in me.loops:
				custom_normals[loop.vertex_index] = loop.normal.copy()

		cm_verts = []
		cm_norms = []
		cm_uvs = []
		# 頂点情報を書き出し
		for i, vert in enumerate(bm.verts):
			co = vert.co * self.scale
			if me.has_custom_normals:
				no = custom_normals[vert.index]
			else:
				no = vert.normal.copy()
			for uv in vert_uvs[i]:
				cm_verts.append(co)
				cm_norms.append(no)
				cm_uvs.append(uv)
				file.write(struct.pack('<3f', -co.x, co.y, co.z))
				file.write(struct.pack('<3f', -no.x, no.y, no.z))
				file.write(struct.pack('<2f', uv.x, uv.y))
		context.window_manager.progress_update(6)

		cm_tris = self.parse_triangles(bm, ob, uv_lay, vert_iuv, vert_indices)

		# 接空間情報を書き出し
		if self.export_tangent:
			tangents = self.calc_tangents(cm_tris, cm_verts, cm_norms, cm_uvs)
			file.write(struct.pack('<i', len(tangents)))
			for t in tangents:
				file.write(struct.pack('<4f', *t))
		else:
			file.write(struct.pack('<i', 0))

		# ウェイト情報を書き出し
		for vert in vertices:
			for uv in vert_uvs[vert['index']]:
				file.write(struct.pack('<4H', *vert['face_indexs']))
				file.write(struct.pack('<4f', *vert['weights']))
		context.window_manager.progress_update(7)
		
		# 面情報を書き出し
		for tri in cm_tris:
			file.write(struct.pack('<i', len(tri)))
			for vert_index in tri:
				file.write(struct.pack('<H', vert_index))
		context.window_manager.progress_update(8)
		
		# マテリアルを書き出し
		file.write(struct.pack('<i', len(ob.material_slots)))
		for slot_index, slot in enumerate(ob.material_slots):
			if self.mate_info_mode == 'MATERIAL':
				mate = slot.material
				common.write_str(file, common.remove_serial_number(mate.name, self.is_arrange_name))
				common.write_str(file, mate['shader1'])
				common.write_str(file, mate['shader2'])
				for tindex, tslot in enumerate(mate.texture_slots):
					if not tslot:
						continue
					tex = tslot.texture
					if mate.use_textures[tindex]:
						common.write_str(file, 'tex')
						common.write_str(file, common.remove_serial_number(tex.name, self.is_arrange_name))
						if tex.image:
							img = tex.image
							common.write_str(file, 'tex2d')
							
							tex_name = common.remove_serial_number(img.name, self.is_arrange_name)
							tex_name = re.sub(r"\.[Pp][Nn][Gg]$", "", tex_name)
							common.write_str(file, tex_name)
							
							if 'cm3d2_path' in img:
								path = img['cm3d2_path']
							else:
								path = bpy.path.abspath(img.filepath)
							path = path.replace('\\', '/')
							path = re.sub(r'^[\/\.]*', "", path)
							if not re.search(r'^assets/texture/', path, re.I):
								path = "Assets/texture/texture/" + os.path.basename(path)
							common.write_str(file, path)
							col = tslot.color
							file.write(struct.pack('<3f', col[0], col[1], col[2]))
							file.write(struct.pack('<f', tslot.diffuse_color_factor))
						else:
							common.write_str(file, 'null')
					else:
						if tslot.use_rgb_to_intensity:
							common.write_str(file, 'col')
							common.write_str(file, common.remove_serial_number(tex.name, self.is_arrange_name))
							col = tslot.color
							file.write(struct.pack('<3f', col[0], col[1], col[2]))
							file.write(struct.pack('<f', tslot.diffuse_color_factor))
						else:
							common.write_str(file, 'f')
							common.write_str(file, common.remove_serial_number(tex.name, self.is_arrange_name))
							file.write(struct.pack('<f', tslot.diffuse_color_factor))
			elif self.mate_info_mode == 'TEXT':
				data = context.blend_data.texts["Material:" + str(slot_index)].as_string()
				data = data.split('\n')
				common.write_str(file, data[2])
				common.write_str(file, data[3])
				common.write_str(file, data[4])
				seek = 5
				for i in range(9**9):
					if len(data) <= seek:
						break
					type = data[seek]
					if type == 'tex':
						common.write_str(file, type)
						common.write_str(file, common.line_trim(data[seek + 1]))
						common.write_str(file, common.line_trim(data[seek + 2]))
						if common.line_trim(data[seek + 2]) == 'tex2d':
							common.write_str(file, common.line_trim(data[seek + 3]))
							common.write_str(file, common.line_trim(data[seek + 4]))
							col = common.line_trim(data[seek + 5])
							col = col.split(' ')
							file.write(struct.pack('<4f', float(col[0]), float(col[1]), float(col[2]), float(col[3])))
							seek += 3
						seek += 2
					elif type == 'col':
						common.write_str(file, type)
						common.write_str(file, common.line_trim(data[seek + 1]))
						col = common.line_trim(data[seek + 2])
						col = col.split(' ')
						file.write(struct.pack('<4f', float(col[0]), float(col[1]), float(col[2]), float(col[3])))
						seek += 2
					elif type == 'f':
						common.write_str(file, type)
						common.write_str(file, common.line_trim(data[seek + 1]))
						file.write(struct.pack('<f', float(common.line_trim(data[seek + 2]))))
						seek += 2
					seek += 1
			common.write_str(file, 'end')
		context.window_manager.progress_update(9)
		
		# モーフを書き出し
		if me.shape_keys:
			temp_me = context.blend_data.meshes.new(me.name + ".temp")
			vs = [vert.co for vert in me.vertices]
			es = []
			fs = [face.vertices for face in me.polygons]
			temp_me.from_pydata(vs, es, fs)
			if 2 <= len(me.shape_keys.key_blocks):
				for shape_key in me.shape_keys.key_blocks[1:]:
					morph = []
					vert_index = 0
					for i in range(len(me.vertices)):
						temp_me.vertices[i].co = shape_key.data[i].co.copy()
					temp_me.update()
					for i, vert in enumerate(me.vertices):
						co_diff = shape_key.data[i].co - vert.co
						if me.has_custom_normals:
							no_diff = custom_normals[i] - vert.normal
						else:
							no_diff = temp_me.vertices[i].normal - vert.normal
						if 0.001 < co_diff.length or 0.001 < no_diff.length:
							co = co_diff * self.scale
							for d in vert_uvs[i]:
								morph.append((vert_index, co, no_diff))
								vert_index += 1
						else:
							vert_index += len(vert_uvs[i])
					if prefs.skip_shapekey and not len(morph):

						continue
					common.write_str(file, 'morph')
					common.write_str(file, shape_key.name)
					file.write(struct.pack('<i', len(morph)))
					for v_index, vec, normal in morph:
						file.write(struct.pack('<H', v_index))
						file.write(struct.pack('<3f', -vec.x, vec.y, vec.z))
						file.write(struct.pack('<3f', -normal.x, normal.y, normal.z))
			context.blend_data.meshes.remove(temp_me)
		common.write_str(file, 'end')
 
 
	def parse_triangles(self, bm, ob, uv_lay, vert_iuv, vert_indices):
		def vert_index_from_loops(loops):
			"""vert_index generator"""
			for loop in loops:
				uv = loop[uv_lay].uv
				v_index = loop.vert.index
				vert_index = vert_iuv.get(hash((v_index, uv.x, uv.y)))
				if vert_index is None:
					vert_index = vert_indices.get(v_index, 0)
				yield vert_index

		triangles = []
		for mate_index, slot in enumerate(ob.material_slots):
			tris_faces = []
			for face in bm.faces:
				if face.material_index != mate_index:
					continue
				if len(face.verts) == 3:
					tris_faces.extend(vert_index_from_loops(reversed(face.loops)))
				elif len(face.verts) == 4 and self.is_convert_tris:
					v1 = face.loops[0].vert.co - face.loops[2].vert.co
					v2 = face.loops[1].vert.co - face.loops[3].vert.co
					if v1.length < v2.length:
						f1 = [0, 1, 2]
						f2 = [0, 2, 3]
					else:
						f1 = [0, 1, 3]
						f2 = [1, 2, 3]
					faces, faces2 = [], []
					for i, vert_index in enumerate(vert_index_from_loops(reversed(face.loops))):
						if i in f1:
							faces.append(vert_index)
						if i in f2:
							faces2.append(vert_index)
					tris_faces.extend(faces)
					tris_faces.extend(faces2)
				elif 5 <= len(face.verts) and self.is_convert_tris:
					face_count = len(face.verts) - 2

					tris = []
					seek_min, seek_max = 0, len(face.verts) - 1
					for i in range(face_count):
						if not i % 2:
							tris.append([seek_min, seek_min + 1, seek_max])
							seek_min += 1
						else:
							tris.append([seek_min, seek_max - 1, seek_max])
							seek_max -= 1

					tris_indexs = [[] for _ in range(len(tris))]
					for i, vert_index in enumerate(vert_index_from_loops(reversed(face.loops))):
						for tris_index, points in enumerate(tris):
							if i in points:
								tris_indexs[tris_index].append(vert_index)

					tris_faces.extend(p for ps in tris_indexs for p in ps)

			triangles.append(tris_faces)
		return triangles


	def calc_tangents(self, cm_tris, cm_verts, cm_norms, cm_uvs):
		count = len(cm_verts)
		tan1 = [None] * count
		tan2 = [None] * count
		for i in range(0, count):
			tan1[i] = mathutils.Vector((0, 0, 0))
			tan2[i] = mathutils.Vector((0, 0, 0))

		for tris in cm_tris:
			tri_len = len(tris)
			tri_idx = 0
			while tri_idx < tri_len:
				i1, i2, i3 = tris[tri_idx], tris[tri_idx + 1], tris[tri_idx + 2]
				v1, v2, v3 = cm_verts[i1], cm_verts[i2], cm_verts[i3]
				w1, w2, w3 = cm_uvs[i1], cm_uvs[i2], cm_uvs[i3]

				a1 = v2 - v1
				a2 = v3 - v1
				s1 = w2 - w1
				s2 = w3 - w1

				r = 1.0 / (s1.x * s2.y - s2.x * s1.y)
				sdir = mathutils.Vector(((s2.y * a1.x - s1.y * a2.x) * r, (s2.y * a1.y - s1.y * a2.y) * r, (s2.y * a1.z - s1.y * a2.z) * r))
				tan1[i1] += sdir
				tan1[i2] += sdir
				tan1[i3] += sdir

				tdir = mathutils.Vector(((s1.x * a2.x - s2.x * a1.x) * r, (s1.x * a2.y - s2.x * a1.y) * r, (s1.x * a2.z - s2.x * a1.z) * r))
				tan2[i1] += tdir
				tan2[i2] += tdir
				tan2[i3] += tdir

				tri_idx += 3

		tangents = [None] * count
		for i in range(0, count):
			n = cm_norms[i]
			ti = tan1[i]
			t = (ti - n * n.dot(ti)).normalized()

			c = n.cross(ti)
			val = c.dot(tan2[i])
			w = 1.0 if val < 0 else -1.0
			tangents[i] = (-t.x, t.y, t.z, w)

		return tangents

	def select_no_weight_vertices(self, context, local_bone_name_indices,selected_meshes):
		"""ウェイトが割り当てられていない頂点を選択する"""
		error_ob = selected_meshes[0]
		for ob in selected_meshes:
			bpy.context.scene.objects.active = ob
			me = ob.data
			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.mesh.select_all(action='DESELECT')
			bpy.ops.object.mode_set(mode='OBJECT')		
			context.tool_settings.mesh_select_mode = (True, False, False)
			for vert in me.vertices:
				for vg in vert.groups:
					name = common.encode_bone_name(ob.vertex_groups[vg.group].name, self.is_convert_bone_weight_names)
					if name in local_bone_name_indices and 0.0 < vg.weight:
						break
				else:
					vert.select = True
					error_ob = ob
		bpy.context.scene.objects.active = error_ob
		bpy.ops.object.mode_set(mode='EDIT')

	def armature_bone_data_parser(self, ob):
		"""アーマチュアを解析してBoneDataを返す"""
		arm = ob.data
		
		bones = []
		bone_name_indices = {}
		already_bone_names = []
		bones_queue = arm.bones[:]
		while len(bones_queue):
			bone = bones_queue.pop(0)
			
			if not bone.parent:
				already_bone_names.append(bone.name)
				bones.append(bone)
				bone_name_indices[bone.name] = len(bone_name_indices)
				continue
			elif bone.parent.name in already_bone_names:
				already_bone_names.append(bone.name)
				bones.append(bone)
				bone_name_indices[bone.name] = len(bone_name_indices)
				continue
			
			bones_queue.append(bone)
		
		bone_data = []
		for bone in bones:
			
			if 'UnknownFlag' in bone: unknown_frag = bone['UnknownFlag']
			else: unknown_frag = 0
			
			if bone.parent: parent_index = bone_name_indices[bone.parent.name]
			else: parent_index = -1
			
			mat = bone.matrix_local.copy()
			if bone.parent:
				mat = bone.parent.matrix_local.inverted() * mat
			
			co = mat.to_translation() * self.scale
			rot = mat.to_quaternion()
			
			if bone.parent:
				co.x, co.y, co.z = -co.y, -co.x, co.z
				rot.w, rot.x, rot.y, rot.z = rot.w, rot.y, rot.x, -rot.z
			else:
				co.x, co.y, co.z = -co.x, co.z, -co.y
				
				fix_quat = mathutils.Euler((0, 0, math.radians(-90)), 'XYZ').to_quaternion()
				fix_quat2 = mathutils.Euler((math.radians(-90), 0, 0), 'XYZ').to_quaternion()
				rot = rot * fix_quat * fix_quat2
				
				rot.w, rot.x, rot.y, rot.z = -rot.y, -rot.z, -rot.x, rot.w
			
			bone_data.append({
				'name': bone.name,
				'unknown': unknown_frag,
				'parent_index': parent_index,
				'co': co.copy(),
				'rot': rot.copy(),
				})
		return bone_data

	@staticmethod
	def bone_data_parser(container):
		"""BoneData テキストをパースして辞書を要素とするリストを返す"""
		bone_data = []
		bone_name_indices = {}
		for line in container:
			data = line.split(',')
			if len(data) < 5:
				continue
			
			parent_name = data[2]
			if parent_name.isdigit():
				parent_index = int(parent_name)
			else:
				parent_index = bone_name_indices.get(parent_name, -1)

			bone_datum = {
				'name': data[0],
				'unknown': int(data[1]),
				'parent_index': parent_index,
				'co': list(map(float, data[3].split())),
				'rot': list(map(float, data[4].split())),
				}
			# scale info (for version 2001 or later)
			if len(data) >= 7:
				if data[5] == '1':
					bone_scale = data[6]
					bone_datum['scale'] = list(map(float, bone_scale.split()))
			bone_data.append(bone_datum)
			bone_name_indices[data[0]] = len(bone_name_indices)
		return bone_data

	def armature_local_bone_data_parser(self, ob):
		"""アーマチュアを解析してBoneDataを返す"""
		arm = ob.data
		
		bones = []
		bone_name_indices = {}
		already_bone_names = []
		bones_queue = arm.bones[:]
		while len(bones_queue):
			bone = bones_queue.pop(0)
			
			if not bone.parent:
				already_bone_names.append(bone.name)
				bones.append(bone)
				bone_name_indices[bone.name] = len(bone_name_indices)
				continue
			elif bone.parent.name in already_bone_names:
				already_bone_names.append(bone.name)
				bones.append(bone)
				bone_name_indices[bone.name] = len(bone_name_indices)
				continue
			
			bones_queue.append(bone)
		
		local_bone_data = []
		for bone in bones:
			
			mat = bone.matrix_local.copy()
			
			co = mat.to_translation() * self.scale
			rot = mat.to_quaternion()
			
			co.rotate(rot.inverted())
			co.x, co.y, co.z = co.y, co.x, -co.z
			
			fix_quat = mathutils.Euler((0, 0, math.radians(-90)), 'XYZ').to_quaternion()
			rot = rot * fix_quat
			rot.w, rot.x, rot.y, rot.z = -rot.z, -rot.y, -rot.x, rot.w
			
			co_mat = mathutils.Matrix.Translation(co)
			rot_mat = rot.to_matrix().to_4x4()
			mat = co_mat * rot_mat
			
			copy_mat = mat.copy()
			mat[0][0], mat[0][1], mat[0][2], mat[0][3] = copy_mat[0][0], copy_mat[1][0], copy_mat[2][0], copy_mat[3][0]
			mat[1][0], mat[1][1], mat[1][2], mat[1][3] = copy_mat[0][1], copy_mat[1][1], copy_mat[2][1], copy_mat[3][1]
			mat[2][0], mat[2][1], mat[2][2], mat[2][3] = copy_mat[0][2], copy_mat[1][2], copy_mat[2][2], copy_mat[3][2]
			mat[3][0], mat[3][1], mat[3][2], mat[3][3] = copy_mat[0][3], copy_mat[1][3], copy_mat[2][3], copy_mat[3][3]
			
			mat_array = []
			for vec in mat:
				mat_array.extend(vec[:])
			
			local_bone_data.append({
				'name': bone.name,
				'matrix': mat_array,
				})
		return local_bone_data

	@staticmethod
	def local_bone_data_parser(container):
		"""LocalBoneData テキストをパースして辞書を要素とするリストを返す"""
		local_bone_data = []
		for line in container:
			data = line.split(',')
			if len(data) != 2:
				continue
			local_bone_data.append({
				'name': data[0],
				'matrix': list(map(float, data[1].split())),
				})
		return local_bone_data


	@staticmethod
	def indexed_data_generator(container, prefix='', max_index=9**9, max_pass=50):
		"""コンテナ内の数値インデックスをキーに持つ要素を昇順に返すジェネレーター"""
		pass_count = 0
		for i in range(max_index):
			name = prefix + str(i)
			if name not in container:
				pass_count += 1
				if max_pass < pass_count:
					return
				continue
			yield container[name]



# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_model.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
