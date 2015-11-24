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
		('TEXT', "テキスト", "", 1),
		('OBJECT', "オブジェクト内プロパティ", "", 2),
		('ARMATURE', "アーマチュア内プロパティ", "", 3),
		]
	bone_info_mode = bpy.props.EnumProperty(items=items, name="ボーン情報元", default='OBJECT', description="modelファイルに必要なボーン情報をどこから引っ張ってくるか選びます")
	
	items = [
		('TEXT', "テキスト", "", 1),
		('MATERIAL', "マテリアル", "", 2),
		]
	mate_info_mode = bpy.props.EnumProperty(items=items, name="マテリアル情報元", default='MATERIAL', description="modelファイルに必要なマテリアル情報をどこから引っ張ってくるか選びます")
	
	is_arrange_name = bpy.props.BoolProperty(name="データ名の連番を削除", default=True, description="「○○.001」のような連番が付属したデータ名からこれらを削除します")
	
	is_convert_tris = bpy.props.BoolProperty(name="四角面を三角面に", default=True, description="四角ポリゴンを三角ポリゴンに変換してから出力します、元のメッシュには影響ありません")
	is_normalize_weight = bpy.props.BoolProperty(name="ウェイトの合計を1.0に", default=True, description="4つのウェイトの合計値が1.0になるように正規化します")
	is_convert_vertex_group_names = bpy.props.BoolProperty(name="頂点グループ名をCM3D2用に変換", default=True, description="全ての頂点グループ名をCM3D2で使える名前にしてからエクスポートします")
	
	def invoke(self, context, event):
		# データの成否チェック
		ob = context.active_object
		if not ob:
			self.report(type={'ERROR'}, message="アクティブオブジェクトがありません")
			return {'CANCELLED'}
		if ob.type != 'MESH':
			self.report(type={'ERROR'}, message="メッシュオブジェクトを選択した状態で実行してください")
			return {'CANCELLED'}
		if not len(ob.material_slots):
			self.report(type={'ERROR'}, message="マテリアルがありません")
			return {'CANCELLED'}
		for slot in ob.material_slots:
			if not slot.material:
				self.report(type={'ERROR'}, message="空のマテリアルスロットを削除してください")
				return {'CANCELLED'}
			try:
				slot.material['shader1']
				slot.material['shader2']
			except:
				self.report(type={'ERROR'}, message="マテリアルに「shader1」と「shader2」という名前のカスタムプロパティを用意してください")
				return {'CANCELLED'}
		me = ob.data
		if not me.uv_layers.active:
			self.report(type={'ERROR'}, message="UVがありません")
			return {'CANCELLED'}
		ob_names = common.remove_serial_number(ob.name, self.is_arrange_name).split('.')
		#if len(ob_names) != 2:
		#	self.report(type={'ERROR'}, message="オブジェクト名は「○○○.○○○」という形式にしてください")
		#	return {'CANCELLED'}
		if 65535 < len(me.vertices):
			self.report(type={'ERROR'}, message="エクスポート可能な頂点数を大幅に超えています、最低でも65535未満には削減してください")
			return {'CANCELLED'}
		for face in me.polygons:
			if 5 <= len(face.vertices):
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.select_all(action='DESELECT')
				bpy.ops.object.mode_set(mode='OBJECT')
				context.tool_settings.mesh_select_mode = (False, False, True)
				for face in me.polygons:
					if 5 <= len(face.vertices):
						face.select = True
				bpy.ops.object.mode_set(mode='EDIT')
				self.report(type={'ERROR'}, message="五角以上のポリゴンが含まれています")
				return {'CANCELLED'}
		
		# model名とか
		self.model_name = ob_names[0]
		if 2 <= len(ob_names):
			self.base_bone_name = ob_names[1]
		else:
			self.base_bone_name = 'body'
		
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
		self.filepath = common.default_cm3d2_dir(context.user_preferences.addons[__name__.split('.')[0]].preferences.model_export_path, ob_names[0], "model")
		
		# バックアップ関係
		self.is_backup = bool(context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext)
		
		self.scale = 1.0 / context.user_preferences.addons[__name__.split('.')[0]].preferences.scale
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'scale')
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext:
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
		sub_box.prop(self, 'is_convert_vertex_group_names', icon='GROUP_VERTEX')
	
	def execute(self, context):
		start_time = time.time()
		
		context.user_preferences.addons[__name__.split('.')[0]].preferences.model_export_path = self.filepath
		context.window_manager.progress_begin(0, 100)
		context.window_manager.progress_update(0)
		
		ob = context.active_object
		me = ob.data
		
		# データの成否チェック
		if self.bone_info_mode == 'TEXT':
			if "BoneData" not in context.blend_data.texts.keys():
				self.report(type={'ERROR'}, message="テキスト「BoneData」が見つかりません、中止します")
				return {'CANCELLED'}
			elif "LocalBoneData" not in context.blend_data.texts.keys():
				self.report(type={'ERROR'}, message="テキスト「LocalBoneData」が見つかりません、中止します")
				return {'CANCELLED'}
		elif self.bone_info_mode == 'OBJECT':
			if "BoneData:0" not in ob.keys():
				self.report(type={'ERROR'}, message="オブジェクトのカスタムプロパティにボーン情報がありません")
				return {'CANCELLED'}
			elif "LocalBoneData:0" not in ob.keys():
				self.report(type={'ERROR'}, message="オブジェクトのカスタムプロパティにボーン情報がありません")
				return {'CANCELLED'}
		elif self.bone_info_mode == 'ARMATURE':
			arm_ob = ob.parent
			if arm_ob:
				if arm_ob.type == 'ARMATURE':
					if "BoneData:0" not in arm_ob.data.keys():
						self.report(type={'ERROR'}, message="アーマチュアのカスタムプロパティにボーン情報がありません")
						return {'CANCELLED'}
					elif "LocalBoneData:0" not in arm_ob.data.keys():
						self.report(type={'ERROR'}, message="アーマチュアのカスタムプロパティにボーン情報がありません")
						return {'CANCELLED'}
				else:
					self.report(type={'ERROR'}, message="メッシュオブジェクトの親がアーマチュアではありません")
					return {'CANCELLED'}
			else:
				for mod in ob.modifiers:
					if mod.type == 'ARMATURE':
						if mod.object:
							arm_ob = mod.object
							if "BoneData:0" not in arm_ob.data.keys():
								self.report(type={'ERROR'}, message="アーマチュアのカスタムプロパティにボーン情報がありません")
								return {'CANCELLED'}
							elif "LocalBoneData:0" not in arm_ob.data.keys():
								self.report(type={'ERROR'}, message="アーマチュアのカスタムプロパティにボーン情報がありません")
								return {'CANCELLED'}
							break
				else:
					self.report(type={'ERROR'}, message="アーマチュアが見つかりません、親にするかモディファイアにして下さい")
					return {'CANCELLED'}
			if "BoneData:0" not in arm_ob.data.keys():
				self.report(type={'ERROR'}, message="アーマチュアのカスタムプロパティにボーン情報がありません")
				return {'CANCELLED'}
			elif "LocalBoneData:0" not in arm_ob.data.keys():
				self.report(type={'ERROR'}, message="アーマチュアのカスタムプロパティにボーン情報がありません")
				return {'CANCELLED'}
		else:
			self.report(type={'ERROR'}, message="ボーン情報元のモードがおかしいです")
			return {'CANCELLED'}
		
		if self.mate_info_mode == 'TEXT':
			for index, slot in enumerate(ob.material_slots):
				if "Material:" + str(index) not in context.blend_data.texts.keys():
					self.report(type={'ERROR'}, message="マテリアル情報元のテキストが足りません")
					return {'CANCELLED'}
		context.window_manager.progress_update(1)
		
		ob_names = common.remove_serial_number(ob.name, self.is_arrange_name).split('.')
		ob_names = [self.model_name, self.base_bone_name]
		
		# BoneData情報読み込み
		bone_data = []
		if self.bone_info_mode == 'TEXT':
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
			pass_count = 0
			for i in range(9**9):
				name = "BoneData:" + str(i)
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
			self.report(type={'ERROR'}, message="テキスト「BoneData」に有効なデータがありません")
			return {'CANCELLED'}
		
		for bone in bone_data:
			if bone['name'] == ob_names[1]:
				break
		else:
			self.report(type={'ERROR'}, message="オブジェクト名の後半は存在するボーン名にして下さい")
			return {'CANCELLED'}
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
			self.report(type={'ERROR'}, message="テキスト「LocalBoneData」に有効なデータがありません")
			return {'CANCELLED'}
		context.window_manager.progress_update(3)
		
		# バックアップ
		if self.is_backup and context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext:
			if os.path.exists(self.filepath):
				backup_path = self.filepath + "." + context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext
				shutil.copyfile(self.filepath, backup_path)
				self.report(type={'INFO'}, message="上書き時にバックアップを複製しました")
		
		# ファイル先頭
		file = open(self.filepath, 'wb')
		
		common.write_str(file, 'CM3D2_MESH')
		file.write(struct.pack('<i', self.version))
		
		common.write_str(file, ob_names[0])
		common.write_str(file, ob_names[1])
		
		# ボーン情報書き出し
		file.write(struct.pack('<i', len(bone_data)))
		for bone in bone_data:
			common.write_str(file, bone['name'])
			file.write(struct.pack('<b', bone['unknown']))
		context.window_manager.progress_update(3.1)
		for bone in bone_data:
			file.write(struct.pack('<i', bone['parent_index']))
		context.window_manager.progress_update(3.2)
		for bone in bone_data:
			file.write(struct.pack('<3f', bone['co'][0], bone['co'][1], bone['co'][2]))
			file.write(struct.pack('<4f', bone['rot'][1], bone['rot'][2], bone['rot'][3], bone['rot'][0]))
		context.window_manager.progress_update(4)
		
		bpy.ops.object.mode_set(mode='OBJECT')
		
		# 正しい頂点数などを取得
		bm = bmesh.new()
		bm.from_mesh(me)
		uv_lay = bm.loops.layers.uv.active
		vert_uvs = []
		vert_iuv = []
		vert_count = 0
		for vert in bm.verts:
			vert_uvs.append([])
			for loop in vert.link_loops:
				uv = loop[uv_lay].uv
				if uv not in vert_uvs[-1]:
					vert_uvs[-1].append(uv)
					iuv_str = str(vert.index) + " " + str(uv.x) + " " + str(uv.y)
					vert_iuv.append(iuv_str)
					vert_count += 1
		if 65535 < vert_count:
			self.report(type={'ERROR'}, message="頂点数がまだ多いです (現在" + str(vert_count) + "頂点)。あと" + str(vert_count - 65535) + "頂点以上減らしてください、中止します")
			return {'CANCELLED'}
		context.window_manager.progress_update(5)
		
		file.write(struct.pack('<2i', vert_count, len(ob.material_slots)))
		
		# ローカルボーン情報を書き出し
		file.write(struct.pack('<i', len(local_bone_data)))
		for bone in local_bone_data:
			common.write_str(file, bone['name'])
		context.window_manager.progress_update(5.1)
		for bone in local_bone_data:
			for f in bone['matrix']:
				file.write(struct.pack('<f', f))
		context.window_manager.progress_update(5.2)
		
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
		for vert in me.vertices:
			progress_count += progress_plus_value
			context.window_manager.progress_update(progress_count)
			
			vgs = []
			face_indexs = []
			weights = []
			for vg in vert.groups:
				name = common.encode_bone_name(ob.vertex_groups[vg.group].name, self.is_convert_vertex_group_names)
				print(name)
				if name not in local_bone_names:
					continue
				weight = vg.weight
				if 0.0 < weight:
					vgs.append([name, weight])
			if len(vgs) == 0:
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.select_all(action='DESELECT')
				bpy.ops.object.mode_set(mode='OBJECT')
				context.tool_settings.mesh_select_mode = (True, False, False)
				for vert in me.vertices:
					for vg in vert.groups:
						name = common.encode_bone_name(ob.vertex_groups[vg.group].name, self.is_convert_vertex_group_names)
						if name not in local_bone_names:
							continue
						if 0.0 < vg.weight:
							break
					else:
						vert.select = True
				bpy.ops.object.mode_set(mode='EDIT')
				self.report(type={'ERROR'}, message="ウェイトが割り当てられていない頂点が見つかりました、中止します")
				return {'CANCELLED'}
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
			self.report(type={'INFO'}, message="ウェイトの合計が1.0を超えている頂点が%dつ見つかりました" % is_over_one)
		if 1 <= is_under_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0未満の頂点が%dつ見つかりました" % is_under_one)
		context.window_manager.progress_update(7)
		
		# 面情報を書き出し
		error_face_count = 0
		progress_plus_value = 1.0 / (len(ob.material_slots) * len(bm.faces))
		progress_count = 7.0
		for mate_index, slot in enumerate(ob.material_slots):
			face_count = 0
			faces = []
			faces2 = []
			for face in bm.faces:
				progress_count += progress_plus_value
				context.window_manager.progress_update(progress_count)
				if face.material_index != mate_index:
					continue
				if len(face.verts) == 3:
					for loop in face.loops:
						uv = loop[uv_lay].uv
						index = loop.vert.index
						try:
							iuv_str = str(index) + " " + str(uv.x) + " " + str(uv.y)
							vert_index = vert_iuv.index(iuv_str)
						except ValueError:
							vert_index = 0
							for i, s in enumerate(vert_iuv):
								if int(s.split(' ')[0]) == index:
									vert_index = i
									break
						faces.append(vert_index)
					face_count += 1
				elif len(face.verts) == 4 and self.is_convert_tris:
					v1 = face.loops[0].vert.co - face.loops[2].vert.co
					v2 = face.loops[1].vert.co - face.loops[3].vert.co
					if v1.length < v2.length:
						f1 = [0, 1, 2]
						f2 = [0, 2, 3]
					else:
						f1 = [0, 1, 3]
						f2 = [1, 2, 3]
					for i, loop in enumerate(face.loops):
						if i in f1:
							uv = loop[uv_lay].uv
							index = loop.vert.index
							iuv_str = str(index) + " " + str(uv.x) + " " + str(uv.y)
							vert_index = vert_iuv.index(iuv_str)
							faces.append(vert_index)
						if i in f2:
							uv = loop[uv_lay].uv
							index = loop.vert.index
							iuv_str = str(index) + " " + str(uv.x) + " " + str(uv.y)
							vert_index = vert_iuv.index(iuv_str)
							faces2.append(vert_index)
					face_count += 2
				else:
					error_face_count += 1
					continue
			file.write(struct.pack('<i', face_count * 3))
			faces.reverse()
			for face in faces:
				file.write(struct.pack('<H', face))
			if len(faces2):
				faces2.reverse()
				for face in faces2:
					file.write(struct.pack('<H', face))
		if 1 <= error_face_count:
			self.report(type={'INFO'}, message="多角ポリゴンが%dつ見つかりました、正常に出力できなかった可能性があります" % error_face_count)
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
			#for edge in me.edges:
			#	es.append(edge.vertices)
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
		self.report(type={'INFO'}, message="modelのエクスポートが完了しました、" + str(round(diff_time, 1)) + "秒掛かりました")
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_model.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
