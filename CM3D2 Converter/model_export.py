import bpy, re, os, os.path, struct, shutil, mathutils, bmesh, time
from . import common

# メインオペレーター
class export_cm3d2_model(bpy.types.Operator):
	bl_idname = 'export_mesh.export_cm3d2_model'
	bl_label = "CM3D2 Model (.model)"
	bl_description = "カスタムメイド3D2のmodelファイルを書き出します"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".model"
	filter_glob = bpy.props.StringProperty(default="*.model", options={'HIDDEN'})
	
	scale = bpy.props.FloatProperty(name="倍率", default=0.2, min=0.01, max=100, soft_min=0.01, soft_max=100, step=10, precision=2, description="エクスポート時のメッシュ等の拡大率です")
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	model_name = bpy.props.StringProperty(name="model名", default="*")
	base_bone_name = bpy.props.StringProperty(name="基点ボーン名", default="*")
	
	items = [
		('TEXT', "テキスト", "", 'FILE_TEXT', 1),
		('OBJECT', "オブジェクト内プロパティ", "", 'OBJECT_DATAMODE', 2),
		('ARMATURE', "アーマチュア内プロパティ", "", 'ARMATURE_DATA', 3),
		]
	bone_info_mode = bpy.props.EnumProperty(items=items, name="ボーン情報元", default='OBJECT', description="modelファイルに必要なボーン情報をどこから引っ張ってくるか選びます")
	
	items = [
		('TEXT', "テキスト", "", 'FILE_TEXT', 1),
		('MATERIAL', "マテリアル", "", 'MATERIAL', 2),
		]
	mate_info_mode = bpy.props.EnumProperty(items=items, name="マテリアル情報元", default='MATERIAL', description="modelファイルに必要なマテリアル情報をどこから引っ張ってくるか選びます")
	
	is_arrange_name = bpy.props.BoolProperty(name="データ名の連番を削除", default=True, description="「○○.001」のような連番が付属したデータ名からこれらを削除します")
	
	is_convert_tris = bpy.props.BoolProperty(name="四角面を三角面に", default=True, description="四角ポリゴンを三角ポリゴンに変換してから出力します、元のメッシュには影響ありません")
	is_normalize_weight = bpy.props.BoolProperty(name="ウェイトの合計を1.0に", default=True, description="4つのウェイトの合計値が1.0になるように正規化します")
	is_convert_bone_weight_names = bpy.props.BoolProperty(name="頂点グループ名をCM3D2用に変換", default=True, description="全ての頂点グループ名をCM3D2で使える名前にしてからエクスポートします")
	
	is_batch = bpy.props.BoolProperty(name="バッチモード", default=False, description="モードの切替やエラー個所の選択を行いません")
	
	def report_cancel(self, report_message, report_type={'ERROR'}, return_dict={'CANCELLED'}):
		self.report(type=report_type, message=report_message)
		return return_dict
	
	def precheck(self, context):
		# データの成否チェック
		ob = context.active_object
		if not ob:
			return self.report_cancel("アクティブオブジェクトがありません")
		if ob.type != 'MESH':
			return self.report_cancel("メッシュオブジェクトを選択した状態で実行してください")
		for mod in ob.modifiers:
			if mod.type not in ['ARMATURE', 'SUBSURF']:
				return self.report_cancel("モディファイアを適用するか消してください")
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
		self.base_bone_name = ob_names[1] if 2 <= len(ob_names) else 'body'
		
		# ボーン情報元のデフォルトオプションを取得
		if self.bone_info_mode == 'OBJECT':
			if "BoneData:0" not in ob.keys():
				if "BoneData" in context.blend_data.texts.keys():
					if "LocalBoneData" in context.blend_data.texts.keys():
						self.bone_info_mode = 'TEXT'
				arm_ob = ob.parent
				if arm_ob:
					if arm_ob.type == 'ARMATURE':
						self.bone_info_mode = 'ARMATURE'
				else:
					for mod in ob.modifiers:
						if mod.type == 'ARMATURE':
							if mod.object:
								self.bone_info_mode = 'ARMATURE'
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
		box.prop(self, 'base_bone_name', icon='CONSTRAINT_BONE')
		box = self.layout.box()
		box.prop(self, 'bone_info_mode', icon='BONE_DATA')
		box.prop(self, 'mate_info_mode', icon='MATERIAL')
		box = self.layout.box()
		box.label("メッシュオプション")
		box.prop(self, 'is_convert_tris', icon='MESH_DATA')
		sub_box = box.box()
		sub_box.prop(self, 'is_normalize_weight', icon='MOD_VERTEX_WEIGHT')
		sub_box.prop(self, 'is_convert_bone_weight_names', icon_value=common.preview_collections['main']['KISS'].icon_id)
	
	def execute(self, context):
		start_time = time.time()
		
		if not self.is_batch:
			common.preferences().model_export_path = self.filepath
		
		context.window_manager.progress_begin(0, 10)
		context.window_manager.progress_update(0)
		
		res = self.precheck(context)
		if res: return res

		ob = context.active_object
		me = ob.data
		
		# データの成否チェック
		if self.bone_info_mode == 'TEXT':
			if "BoneData" not in context.blend_data.texts.keys():
				return self.report_cancel("テキスト「BoneData」が見つかりません、中止します")
			if "LocalBoneData" not in context.blend_data.texts.keys():
				return self.report_cancel("テキスト「LocalBoneData」が見つかりません、中止します")
		elif self.bone_info_mode == 'OBJECT':
			if "BoneData:0" not in ob.keys():
				return self.report_cancel("オブジェクトのカスタムプロパティにボーン情報がありません")
			if "LocalBoneData:0" not in ob.keys():
				return self.report_cancel("オブジェクトのカスタムプロパティにボーン情報がありません")
		elif self.bone_info_mode == 'ARMATURE':
			arm_ob = ob.parent
			if arm_ob and arm_ob.type != 'ARMATURE':
				return self.report_cancel("メッシュオブジェクトの親がアーマチュアではありません")
			if not arm_ob:
				try:
					arm_ob = next(mod for mod in ob.modifiers if mod.type == 'ARMATURE' and mod.object)
				except StopIteration:
					return self.report_cancel("アーマチュアが見つかりません、親にするかモディファイアにして下さい")
				arm_ob = arm_ob.object
			if "BoneData:0" not in arm_ob.data.keys():
				return self.report_cancel("アーマチュアのカスタムプロパティにボーン情報がありません")
			if "LocalBoneData:0" not in arm_ob.data.keys():
				return self.report_cancel("アーマチュアのカスタムプロパティにボーン情報がありません")
		else:
			return self.report_cancel("ボーン情報元のモードがおかしいです")
		
		if self.mate_info_mode == 'TEXT':
			for index, slot in enumerate(ob.material_slots):
				if "Material:" + str(index) not in context.blend_data.texts.keys():
					return self.report_cancel("マテリアル情報元のテキストが足りません")
		context.window_manager.progress_update(1)
		
		# model名とか
		ob_names = common.remove_serial_number(ob.name, self.is_arrange_name).split('.')
		if self.model_name == '*':
			self.model_name = ob_names[0]
		if self.base_bone_name == '*':
			self.base_bone_name = ob_names[1] if 2 <= len(ob_names) else 'body'
		
		# BoneData情報読み込み
		base_bone_candidate = None
		bone_data = []
		if self.bone_info_mode == 'TEXT':
			if 'BaseBone' in context.blend_data.texts["BoneData"].keys():
				base_bone_candidate = context.blend_data.texts["BoneData"]['BaseBone']
			for line in context.blend_data.texts["BoneData"].lines:
				data = line.body.split(',')
				if len(data) == 5:
					bone_data.append({})
					bone_data[-1]['name'] = data[0]
					bone_data[-1]['unknown'] = int(data[1])
					if re.search(data[2], r'^\d+$'):
						bone_data[-1]['parent_index'] = int(data[2])
					else:
						for i, b in enumerate(bone_data):
							if b['name'] == data[2]:
								bone_data[-1]['parent_index'] = i
								break
						else:
							bone_data[-1]['parent_index'] = -1
					bone_data[-1]['co'] = []
					floats = data[3].split(' ')
					for f in floats:
						bone_data[-1]['co'].append(float(f))
					bone_data[-1]['rot'] = []
					floats = data[4].split(' ')
					for f in floats:
						bone_data[-1]['rot'].append(float(f))
		elif self.bone_info_mode in ['OBJECT', 'ARMATURE']:
			if self.bone_info_mode == 'OBJECT':
				target = ob
			elif self.bone_info_mode == 'ARMATURE':
				target = arm_ob.data
			if 'BaseBone' in target.keys():
				base_bone_candidate = target['BaseBone']
			pass_count = 0
			for i in range(9**9):
				name = "BoneData:" + str(i)
				if name not in target.keys():
					pass_count += 1
					if 50 < pass_count:
						break
					continue
				data = target[name].split(',')
				if len(data) == 5:
					bone_data.append({})
					bone_data[-1]['name'] = data[0]
					bone_data[-1]['unknown'] = int(data[1])
					if re.search(data[2], r'^\d+$'):
						bone_data[-1]['parent_index'] = int(data[2])
					else:
						for i, b in enumerate(bone_data):
							if b['name'] == data[2]:
								bone_data[-1]['parent_index'] = i
								break
						else:
							bone_data[-1]['parent_index'] = -1
					bone_data[-1]['co'] = []
					floats = data[3].split(' ')
					for f in floats:
						bone_data[-1]['co'].append(float(f))
					bone_data[-1]['rot'] = []
					floats = data[4].split(' ')
					for f in floats:
						bone_data[-1]['rot'].append(float(f))
		if len(bone_data) <= 0:
			return self.report_cancel("テキスト「BoneData」に有効なデータがありません")
		
		for bone in bone_data:
			if bone['name'] == self.base_bone_name:
				break
		else:
			if base_bone_candidate:
				self.base_bone_name = base_bone_candidate
			else:
				return self.report_cancel("オブジェクト名の後半は存在するボーン名にして下さい")
		context.window_manager.progress_update(2)
		
		# LocalBoneData情報読み込み
		local_bone_data = []
		local_bone_names = []
		if self.bone_info_mode == 'TEXT':
			for line in context.blend_data.texts["LocalBoneData"].lines:
				data = line.body.split(',')
				if len(data) == 2:
					local_bone_data.append({})
					local_bone_data[-1]['name'] = data[0]
					local_bone_data[-1]['matrix'] = []
					floats = data[1].split(' ')
					for f in floats:
						local_bone_data[-1]['matrix'].append(float(f))
					local_bone_names.append(data[0])
		elif self.bone_info_mode in ['OBJECT', 'ARMATURE']:
			pass_count = 0
			for i in range(9**9):
				name = "LocalBoneData:" + str(i)
				if self.bone_info_mode == 'OBJECT':
					target = ob
				elif self.bone_info_mode == 'ARMATURE':
					target = arm_ob.data
				if name not in target.keys():
					pass_count += 1
					if 50 < pass_count:
						break
					continue
				data = target[name].split(',')
				if len(data) == 2:
					local_bone_data.append({})
					local_bone_data[-1]['name'] = data[0]
					local_bone_data[-1]['matrix'] = []
					floats = data[1].split(' ')
					for f in floats:
						local_bone_data[-1]['matrix'].append(float(f))
					local_bone_names.append(data[0])
		if len(local_bone_data) <= 0:
			return self.report_cancel("テキスト「LocalBoneData」に有効なデータがありません")
		context.window_manager.progress_update(3)
		
		# バックアップ
		common.file_backup(self.filepath, self.is_backup)
		
		# ファイル先頭
		try:
			file = open(self.filepath, 'wb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可の可能性があります")
			return {'CANCELLED'}
		
		common.write_str(file, 'CM3D2_MESH')
		file.write(struct.pack('<i', self.version))
		
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
		context.window_manager.progress_update(4)
		
		if not self.is_batch:
			bpy.ops.object.mode_set(mode='OBJECT')
		
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
			vert_uvs_append([])
			for loop in vert.link_loops:
				uv = loop[uv_lay].uv
				if uv not in vert_uvs[-1]:
					vert_uvs[-1].append(uv)
					iuv_hash = hash(repr([vert.index, uv.x, uv.y]))
					vert_iuv[iuv_hash] = vert_count
					vert_indices[vert.index] = vert_count
					vert_count += 1
		if 65535 < vert_count:
			return self.report_cancel("頂点数がまだ多いです (現在%d頂点)。あと%d頂点以上減らしてください、中止します" % (vert_count, vert_count - 65535))
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
		
		# 頂点情報を書き出し
		for i, vert in enumerate(bm.verts):
			for uv in vert_uvs[i]:
				co = vert.co.copy()
				co *= self.scale
				file.write(struct.pack('<3f', -co.x, co.y, co.z))
				no = vert.normal.copy()
				file.write(struct.pack('<3f', -no.x, no.y, no.z))
				file.write(struct.pack('<2f', uv.x, uv.y))
		context.window_manager.progress_update(6)
		# ウェイト情報を書き出し
		is_over_one = 0
		is_under_one = 0
		file.write(struct.pack('<i', 0))
		progress_plus_value = 1.0 / len(me.vertices)
		progress_count = 6.0
		progress_reduce = len(me.vertices) // 200 + 1
		for vert in me.vertices:
			progress_count += progress_plus_value
			if vert.index % progress_reduce == 0:
				context.window_manager.progress_update(progress_count)
			
			vgs = []
			face_indexs = []
			weights = []
			for vg in vert.groups:
				name = common.encode_bone_name(ob.vertex_groups[vg.group].name, self.is_convert_bone_weight_names)
				if name not in local_bone_names:
					continue
				weight = vg.weight
				if 0.0 < weight:
					vgs.append([name, weight])
			if len(vgs) == 0:
				if not self.is_batch:
					bpy.ops.object.mode_set(mode='EDIT')
					bpy.ops.mesh.select_all(action='DESELECT')
					bpy.ops.object.mode_set(mode='OBJECT')
					context.tool_settings.mesh_select_mode = (True, False, False)
					for vert in me.vertices:
						for vg in vert.groups:
							name = common.encode_bone_name(ob.vertex_groups[vg.group].name, self.is_convert_bone_weight_names)
							if name not in local_bone_names:
								continue
							if 0.0 < vg.weight:
								break
						else:
							vert.select = True
					bpy.ops.object.mode_set(mode='EDIT')
				return self.report_cancel("ウェイトが割り当てられていない頂点が見つかりました、中止します")
			vgs.sort(key=lambda vg: vg[1])
			vgs.reverse()
			for i in range(4):
				try:
					name = vgs[i][0]
				except IndexError:
					index = 0
				else:
					index = 0
					for i, bone in enumerate(local_bone_data):
						if bone['name'] == name:
							break
						index += 1
					else:
						index = 0
				face_indexs.append(index)
			total = 0.0
			for i in range(4):
				try:
					weight = vgs[i][1]
				except IndexError:
					weight = 0.0
				total += weight
			if self.is_normalize_weight:
				for i in range(4):
					try:
						weight = vgs[i][1]
					except IndexError:
						pass
					else:
						weight /= total
						vgs[i][1] = weight
			else:
				if 1.01 < total:
					is_over_one += 1
				if total < 0.99:
					is_under_one += 1
			for i in range(4):
				try:
					weight = vgs[i][1]
				except IndexError:
					if total <= 0.0:
						if i == 0:
							weight = 1.0
					else:
						weight = 0.0
				weights.append(weight)
			
			for uv in vert_uvs[vert.index]:
				for index in face_indexs:
					file.write(struct.pack('<H', index))
				for weight in weights:
					file.write(struct.pack('<f', weight))
		if 1 <= is_over_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0を超えている頂点が見つかりました" % is_over_one)
		if 1 <= is_under_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0未満の頂点が見つかりました" % is_under_one)
		context.window_manager.progress_update(7)
		
		# 面情報を書き出し
		error_face_count = 0
		progress_plus_value = 1.0 / (len(ob.material_slots) * len(bm.faces))
		progress_count = 7.0
		progress_reduce = (len(ob.material_slots) * len(bm.faces)) // 200 + 1
		for mate_index, slot in enumerate(ob.material_slots):
			tris_faces = []
			tris_faces_append = tris_faces.append
			for face in bm.faces:
				progress_count += progress_plus_value
				if face.index % progress_reduce == 0:
					context.window_manager.progress_update(progress_count)
				if face.material_index != mate_index:
					continue
				if len(face.verts) == 3:
					for loop in reversed(face.loops):
						uv = loop[uv_lay].uv
						index = loop.vert.index
						iuv_hash = hash(repr([index, uv.x, uv.y]))
						vert_index = vert_iuv.get(iuv_hash)
						if vert_index is None:
							vert_index = vert_indices.get(index, 0)
						tris_faces_append(vert_index)
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
					for i, loop in enumerate(reversed(face.loops)):
						uv = loop[uv_lay].uv
						iuv_hash = hash(repr([loop.vert.index, uv.x, uv.y]))
						vert_index = vert_iuv.get(iuv_hash)
						if i in f1:
							faces.append(vert_index)
						if i in f2:
							faces2.append(vert_index)
					for i in faces:
						tris_faces_append(i)
					for i in faces2:
						tris_faces_append(i)
				elif 5 <= len(face.verts) and self.is_convert_tris:
					face_count = len(face.verts) - 2
					
					tris = []
					seek_min, seek_max = 0, len(face.verts) - 1
					for i in range(face_count):
						if not i % 2:
							tris.append([seek_min, seek_min+1, seek_max])
							seek_min += 1
						else:
							tris.append([seek_min, seek_max-1, seek_max])
							seek_max -= 1
					
					tris_indexs = [[] for i in tris]
					for i, loop in enumerate(reversed(face.loops)):
						
						uv = loop[uv_lay].uv
						iuv_hash = hash(repr([loop.vert.index, uv.x, uv.y]))
						vert_index = vert_iuv.get(iuv_hash)
						
						for tris_index, points in enumerate(tris):
							if i in points:
								tris_indexs[tris_index].append(vert_index)
					
					tris_faces.extend([p for ps in tris_indexs for p in ps])
			
			file.write(struct.pack('<i', len(tris_faces)))
			for face_index in tris_faces:
				file.write(struct.pack('<H', face_index))
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
							common.write_str(file, common.remove_serial_number(img.name, self.is_arrange_name))
							if 'cm3d2_path' in img.keys():
								path = img['cm3d2_path']
							else:
								path = img.filepath
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
			vs, es, fs = [], [], []
			for vert in me.vertices:
				vs.append(vert.co)
			for face in me.polygons:
				fs.append(face.vertices)
			temp_me.from_pydata(vs, es, fs)
			if 2 <= len(me.shape_keys.key_blocks):
				for shape_key in me.shape_keys.key_blocks[1:]:
					morph = []
					vert_index = 0
					for i in range(len(me.vertices)):
						temp_me.vertices[i].co = shape_key.data[i].co.copy()
					temp_me.update()
					for i, vert in enumerate(me.vertices):
						for d in vert_uvs[i]:
							co_diff = shape_key.data[i].co - vert.co
							no_diff = temp_me.vertices[i].normal - vert.normal
							if 0.001 < co_diff.length or 0.001 < no_diff.length:
								co = co_diff
								co *= self.scale
								morph.append((vert_index, co, i))
							vert_index += 1
					if not len(morph):
						continue
					common.write_str(file, 'morph')
					common.write_str(file, shape_key.name)
					file.write(struct.pack('<i', len(morph)))
					for index, vec, raw_index in morph:
						vec.x = -vec.x
						file.write(struct.pack('<H', index))
						file.write(struct.pack('<3f', vec.x, vec.y, vec.z))
						normal = temp_me.vertices[raw_index].normal.copy() - me.vertices[raw_index].normal.copy()
						file.write(struct.pack('<3f', -normal.x, normal.y, normal.z))
			context.blend_data.meshes.remove(temp_me)
		common.write_str(file, 'end')
		
		file.close()
		context.window_manager.progress_update(10)
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		self.report(type={'INFO'}, message="modelのエクスポートが完了しました")
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_model.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
