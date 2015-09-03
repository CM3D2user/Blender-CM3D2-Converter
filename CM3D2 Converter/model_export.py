import bpy, re, os, struct, mathutils, bmesh

def ArrangeName(name, flag):
	if flag:
		return re.sub(r'\.\d{3}$', "", name)
	return name

def WriteStr(file, s):
	str_count = len(s.encode('utf-8'))
	if 128 <= str_count:
		b = (str_count % 128) + 128
		file.write(struct.pack('<B', b))
		b = str_count // 128
		file.write(struct.pack('<B', b))
	else:
		file.write(struct.pack('<B', str_count))
	file.write(s.encode('utf-8'))

def SetMateLine(line):
	return re.sub(r'^[\t ]*', "", line)

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
	
	def draw(self, context):
		self.layout.prop(self, 'scale')
		self.layout.prop(self, 'bone_info_mode', icon='BONE_DATA')
		self.layout.prop(self, 'mate_info_mode', icon='MATERIAL')
		self.layout.prop(self, 'is_arrange_name', icon='SAVE_AS')
		box = self.layout.box()
		box.label("メッシュオプション")
		box.prop(self, 'is_convert_tris', icon='MESH_DATA')
		box.prop(self, 'is_normalize_weight', icon='GROUP_VERTEX')
	
	def invoke(self, context, event):
		# データの成否チェック
		ob = context.active_object
		if not ob:
			self.report(type={'ERROR'}, message="アクティブオブジェクトがありません")
			return {'CANCELLED'}
		if ob.type != 'MESH':
			self.report(type={'ERROR'}, message="メッシュオブジェクトを選択した状態で実行してください")
			return {'CANCELLED'}
		if not ob.active_material:
			self.report(type={'ERROR'}, message="マテリアルがありません")
			return {'CANCELLED'}
		for slot in ob.material_slots:
			if not slot:
				self.report(type={'ERROR'}, message="空のマテリアルスロットがあります")
				return {'CANCELLED'}
			try:
				slot.material['shader1']
				slot.material['shader2']
			except KeyError:
				self.report(type={'ERROR'}, message="マテリアルに「shader1」と「shader2」という名前のカスタムプロパティを用意してください")
				return {'CANCELLED'}
		me = ob.data
		if not me.uv_layers.active:
			self.report(type={'ERROR'}, message="UVがありません")
			return {'CANCELLED'}
		ob_names = ArrangeName(ob.name, self.is_arrange_name).split('.')
		if len(ob_names) != 2:
			self.report(type={'ERROR'}, message="オブジェクト名は「○○○.○○○」という形式にしてください")
			return {'CANCELLED'}
		
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.model_export_path:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					path = winreg.QueryValueEx(key, 'InstallPath')[0]
					path = os.path.join(path, 'GameData', '*.model')
					context.user_preferences.addons[__name__.split('.')[0]].preferences.model_export_path = path
			except:
				pass
		self.filepath = context.user_preferences.addons[__name__.split('.')[0]].preferences.model_export_path
		path = context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path
		root, ext = os.path.splitext(os.path.basename(path))
		if ob_names[0] == root:
			self.filepath = path
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.model_export_path = self.filepath
		
		ob = context.active_object
		me = ob.data
		
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
					pass
				else:
					self.report(type={'ERROR'}, message="メッシュオブジェクトの親がアーマチュアではありません")
					return {'CANCELLED'}
			else:
				for mod in ob.modifiers:
					if mod.type == 'ARMATURE':
						if mod.object:
							arm_ob = mod.object
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
		
		# BoneData情報読み込み
		bone_data = []
		if self.bone_info_mode == 'TEXT':
			for line in context.blend_data.texts["BoneData"].lines:
				data = line.body.split(',')
				if len(data) == 5:
					bone_data.append({})
					bone_data[-1]['name'] = data[0]
					bone_data[-1]['unknown'] = int(data[1])
					bone_data[-1]['parent_index'] = int(data[2])
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
					bone_data[-1]['parent_index'] = int(data[2])
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
		
		# ファイル先頭
		file = open(self.filepath, 'wb')
		
		WriteStr(file, 'CM3D2_MESH')
		file.write(struct.pack('<i', 1000))
		
		ob_names = ArrangeName(ob.name, self.is_arrange_name).split('.')
		WriteStr(file, ob_names[0])
		WriteStr(file, ob_names[1])
		
		# ボーン情報書き出し
		file.write(struct.pack('<i', len(bone_data)))
		for bone in bone_data:
			WriteStr(file, bone['name'])
			file.write(struct.pack('<b', bone['unknown']))
		for bone in bone_data:
			file.write(struct.pack('<i', bone['parent_index']))
		for bone in bone_data:
			file.write(struct.pack('<3f', bone['co'][0], bone['co'][1], bone['co'][2]))
			file.write(struct.pack('<4f', bone['rot'][1], bone['rot'][2], bone['rot'][3], bone['rot'][0]))
		
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
					vert_iuv.append((vert.index, uv.x, uv.y))
					vert_count += 1
		
		file.write(struct.pack('<2i', vert_count, len(ob.material_slots)))
		
		# ローカルボーン情報を書き出し
		file.write(struct.pack('<i', len(local_bone_data)))
		for bone in local_bone_data:
			WriteStr(file, bone['name'])
		for bone in local_bone_data:
			for f in bone['matrix']:
				file.write(struct.pack('<f', f))
		
		# 頂点情報を書き出し
		for i, vert in enumerate(bm.verts):
			for uv in vert_uvs[i]:
				co = vert.co.copy()
				co *= self.scale
				file.write(struct.pack('<3f', -co.x, co.y, co.z))
				no = vert.normal.copy()
				file.write(struct.pack('<3f', -no.x, no.y, no.z))
				file.write(struct.pack('<2f', uv.x, uv.y))
		# ウェイト情報を書き出し
		is_over_one = 0
		is_under_one = 0
		file.write(struct.pack('<i', 0))
		for vert in me.vertices:
			for uv in vert_uvs[vert.index]:
				vgs = []
				for vg in vert.groups:
					name = ob.vertex_groups[vg.group].name
					if name not in local_bone_names:
						continue
					weight = vg.weight
					vgs.append([name, weight])
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
					file.write(struct.pack('<h', index))
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
					file.write(struct.pack('<f', weight))
		if 1 <= is_over_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0を超えている頂点が%dつ見つかりました" % is_over_one)
		if 1 <= is_under_one:
			self.report(type={'INFO'}, message="ウェイトの合計が1.0未満の頂点が%dつ見つかりました" % is_under_one)
		
		# 面情報を書き出し
		error_face_count = 0
		for mate_index, slot in enumerate(ob.material_slots):
			face_count = 0
			faces = []
			faces2 = []
			for face in bm.faces:
				if face.material_index != mate_index:
					continue
				if len(face.verts) == 3:
					for loop in face.loops:
						uv = loop[uv_lay].uv
						index = loop.vert.index
						vert_index = vert_iuv.index((index, uv.x, uv.y))
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
							vert_index = vert_iuv.index((index, uv.x, uv.y))
							faces.append(vert_index)
						if i in f2:
							uv = loop[uv_lay].uv
							index = loop.vert.index
							vert_index = vert_iuv.index((index, uv.x, uv.y))
							faces2.append(vert_index)
					face_count += 2
				else:
					error_face_count += 1
					continue
			file.write(struct.pack('<i', face_count * 3))
			faces.reverse()
			for face in faces:
				file.write(struct.pack('<h', face))
			if len(faces2):
				faces2.reverse()
				for face in faces2:
					file.write(struct.pack('<h', face))
		if 1 <= error_face_count:
			self.report(type={'INFO'}, message="多角ポリゴンが%dつ見つかりました、正常に出力できなかった可能性があります" % error_face_count)
		
		# マテリアルを書き出し
		file.write(struct.pack('<i', len(ob.material_slots)))
		for slot_index, slot in enumerate(ob.material_slots):
			if self.mate_info_mode == 'MATERIAL':
				mate = slot.material
				WriteStr(file, ArrangeName(mate.name, self.is_arrange_name))
				WriteStr(file, mate['shader1'])
				WriteStr(file, mate['shader2'])
				for tindex, tslot in enumerate(mate.texture_slots):
					if not tslot:
						continue
					tex = tslot.texture
					if mate.use_textures[tindex]:
						WriteStr(file, 'tex')
						WriteStr(file, ArrangeName(tex.name, self.is_arrange_name))
						if tex.image:
							img = tex.image
							WriteStr(file, 'tex2d')
							WriteStr(file, ArrangeName(img.name, self.is_arrange_name))
							path = img.filepath
							path = re.sub(r'^[\/\.]', "", path)
							path = path.replace('\\', '/')
							WriteStr(file, path)
							col = tslot.color
							file.write(struct.pack('<3f', col[0], col[1], col[2]))
							file.write(struct.pack('<f', tslot.diffuse_color_factor))
						else:
							WriteStr(file, 'null')
					else:
						if tslot.use_rgb_to_intensity:
							WriteStr(file, 'col')
							WriteStr(file, ArrangeName(tex.name, self.is_arrange_name))
							col = tslot.color
							file.write(struct.pack('<3f', col[0], col[1], col[2]))
							file.write(struct.pack('<f', tslot.diffuse_color_factor))
						else:
							WriteStr(file, 'f')
							WriteStr(file, ArrangeName(tex.name, self.is_arrange_name))
							file.write(struct.pack('<f', tslot.diffuse_color_factor))
			elif self.mate_info_mode == 'TEXT':
				data = context.blend_data.texts["Material:" + str(slot_index)].as_string()
				data = data.split('\n')
				WriteStr(file, data[2])
				WriteStr(file, data[3])
				WriteStr(file, data[4])
				seek = 5
				for i in range(9**9):
					if len(data) <= seek:
						break
					type = data[seek]
					if type == 'tex':
						WriteStr(file, type)
						WriteStr(file, SetMateLine(data[seek + 1]))
						WriteStr(file, SetMateLine(data[seek + 2]))
						if SetMateLine(data[seek + 2]) == 'tex2d':
							WriteStr(file, SetMateLine(data[seek + 3]))
							WriteStr(file, SetMateLine(data[seek + 4]))
							col = SetMateLine(data[seek + 5])
							col = col.split(' ')
							file.write(struct.pack('<4f', float(col[0]), float(col[1]), float(col[2]), float(col[3])))
							seek += 3
						seek += 2
					elif type == 'col':
						WriteStr(file, type)
						WriteStr(file, SetMateLine(data[seek + 1]))
						col = SetMateLine(data[seek + 2])
						col = col.split(' ')
						file.write(struct.pack('<4f', float(col[0]), float(col[1]), float(col[2]), float(col[3])))
						seek += 2
					elif type == 'f':
						WriteStr(file, type)
						WriteStr(file, SetMateLine(data[seek + 1]))
						file.write(struct.pack('<f', float(SetMateLine(data[seek + 2]))))
						seek += 2
					seek += 1
			WriteStr(file, 'end')
		
		# モーフを書き出し
		if me.shape_keys:
			if 2 <= len(me.shape_keys.key_blocks):
				for shape_key in me.shape_keys.key_blocks[1:]:
					WriteStr(file, 'morph')
					WriteStr(file, shape_key.name)
					morph = []
					vert_index = 0
					for i, vert in enumerate(me.vertices):
						for d in vert_uvs[i]:
							if shape_key.data[i].co != vert.co:
								co = shape_key.data[i].co - vert.co
								co *= self.scale
								morph.append((vert_index, co))
							vert_index += 1
					file.write(struct.pack('<i', len(morph)))
					for index, vec in morph:
						vec.x = -vec.x
						file.write(struct.pack('<h', index))
						file.write(struct.pack('<3f', vec.x, vec.y, vec.z))
						file.write(struct.pack('<3f', 0, 0, 0))
		WriteStr(file, 'end')
		
		file.close()
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_model.bl_idname, icon='SPACE2')
