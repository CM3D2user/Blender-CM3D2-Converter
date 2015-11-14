import bpy, os, re, math, struct, mathutils, bmesh

def ReadStr(file):
	str_index = struct.unpack('<B', file.read(1))[0]
	if 128 <= str_index:
		i = struct.unpack('<B', file.read(1))[0]
		str_index += (i * 128) - 128
	return file.read(str_index).decode('utf-8')

def ConvertBoneName(name, enable=True):
	if not enable:
		return name
	direction = re.search(r'[_ ]([rRlL])[_ ]', name)
	if direction:
		direction = direction.groups()[0]
		name = re.sub(r'([_ ])[rRlL]([_ ])', r'\1*\2', name) + "." + direction
	return name

# メインオペレーター
class import_cm3d2_model(bpy.types.Operator):
	bl_idname = 'import_mesh.import_cm3d2_model'
	bl_label = "CM3D2 Model (.model)"
	bl_description = "カスタムメイド3D2のmodelファイルを読み込みます"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".model"
	filter_glob = bpy.props.StringProperty(default="*.model", options={'HIDDEN'})
	
	scale = bpy.props.FloatProperty(name="倍率", default=5, min=0.1, max=100, soft_min=0.1, soft_max=100, step=100, precision=1, description="インポート時のメッシュ等の拡大率です")
	
	is_mesh = bpy.props.BoolProperty(name="メッシュ生成", default=True, description="ポリゴンを読み込みます、大抵の場合オンでOKです")
	is_remove_doubles = bpy.props.BoolProperty(name="重複頂点を結合", default=True, description="UVの切れ目でポリゴンが分かれている仕様なので、インポート時にくっつけます")
	is_seam = bpy.props.BoolProperty(name="シームをつける", default=True, description="UVの切れ目にシームをつけます")
	
	is_convert_vertex_group_names = bpy.props.BoolProperty(name="頂点グループ名をBlender用に変換", default=True, description="全ての頂点グループ名をBlenderの左右対称編集で使えるように変換してから読み込みます")
	is_vertex_group_sort = bpy.props.BoolProperty(name="頂点グループを名前順ソート", default=True, description="頂点グループを名前順でソートします")
	is_remove_empty_vertex_group = bpy.props.BoolProperty(name="割り当てのない頂点グループを削除", default=True, description="全ての頂点に割り当てのない頂点グループを削除します")
	
	is_mate_color = bpy.props.BoolProperty(name="マテリアルに色をつける", default=True, description="modelファイル内の設定値を参照に、マテリアルに色をつけます")
	is_mate_data_text = bpy.props.BoolProperty(name="テキストにマテリアル情報埋め込み", default=True, description="シェーダー情報をテキストに埋め込みます")
	
	is_armature = bpy.props.BoolProperty(name="アーマチュア生成", default=True, description="ウェイトを編集する時に役立つアーマチュアを読み込みます")
	is_armature_clean = bpy.props.BoolProperty(name="不要なボーンを削除", default=True, description="ウェイトが無いボーンを削除します")
	is_armature_arrange = bpy.props.BoolProperty(name="アーマチュア整頓", default=True, description="ボーンを分かりやすい向きに変更します")
	is_convert_bone_names = bpy.props.BoolProperty(name="ボーン名をBlender用に変換", default=True, description="全てのボーン名をBlenderの左右対称編集で使えるように変換してから読み込みます")
	
	is_bone_data_text = bpy.props.BoolProperty(name="テキスト", default=True, description="ボーン情報をテキストとして読み込みます")
	is_bone_data_obj_property = bpy.props.BoolProperty(name="オブジェクトのカスタムプロパティ", default=True, description="メッシュオブジェクトのカスタムプロパティにボーン情報を埋め込みます")
	is_bone_data_arm_property = bpy.props.BoolProperty(name="アーマチュアのカスタムプロパティ", default=True, description="アーマチュアデータのカスタムプロパティにボーン情報を埋め込みます")
	
	def invoke(self, context, event):
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					path = winreg.QueryValueEx(key, 'InstallPath')[0]
					path = os.path.join(path, 'GameData', '*.model')
					context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path = path
			except:
				pass
		self.filepath = context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path
		context.window_manager.fileselect_add(self)
		self.scale = context.user_preferences.addons[__name__.split('.')[0]].preferences.scale
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'scale')
		box = self.layout.box()
		box.prop(self, 'is_mesh', icon='MESH_DATA')
		sub_box = box.box()
		sub_box.label("メッシュ")
		sub_box.prop(self, 'is_remove_doubles', icon='STICKY_UVS_VERT')
		sub_box.prop(self, 'is_seam', icon='KEY_DEHLT')
		sub_box = box.box()
		sub_box.label("頂点グループ")
		sub_box.prop(self, 'is_convert_vertex_group_names', icon='GROUP_VERTEX')
		sub_box.prop(self, 'is_vertex_group_sort', icon='SORTALPHA')
		sub_box.prop(self, 'is_remove_empty_vertex_group', icon='DISCLOSURE_TRI_DOWN')
		sub_box = box.box()
		sub_box.label("マテリアル")
		sub_box.prop(self, 'is_mate_color', icon='COLOR')
		sub_box.prop(self, 'is_mate_data_text', icon='TEXT')
		box = self.layout.box()
		box.prop(self, 'is_armature', icon='ARMATURE_DATA')
		sub_box = box.box()
		sub_box.label("アーマチュア")
		sub_box.prop(self, 'is_armature_clean', icon='X')
		sub_box.prop(self, 'is_armature_arrange', icon='HAIR')
		sub_box.prop(self, 'is_convert_bone_names', icon='BONE_DATA')
		box = self.layout.box()
		box.label("ボーン情報埋め込み場所")
		box.prop(self, 'is_bone_data_text', icon='TEXT')
		box.prop(self, 'is_bone_data_obj_property', icon='OBJECT_DATA')
		box.prop(self, 'is_bone_data_arm_property', icon='ARMATURE_DATA')
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path = self.filepath
		
		file = open(self.filepath, 'rb')
		
		# ヘッダー
		ext = ReadStr(file)
		if ext != 'CM3D2_MESH':
			self.report(type={'ERROR'}, message="これはカスタムメイド3D2のモデルファイルではありません")
			return {'CANCELLED'}
		struct.unpack('<i', file.read(4))[0]
		
		# 何で名前2つあるの？
		model_name1 = ReadStr(file)
		model_name2 = ReadStr(file)
		
		# ボーン情報読み込み
		bone_data = []
		bone_count = struct.unpack('<i', file.read(4))[0]
		for i in range(bone_count):
			bone_data.append({})
			bone_data[i]['name'] = ReadStr(file)
			bone_data[i]['unknown'] = struct.unpack('<B', file.read(1))[0]
		for i in range(bone_count):
			parent_index = struct.unpack('<i', file.read(4))[0]
			parent_name = None
			if parent_index != -1:
				parent_name = bone_data[parent_index]['name']
			bone_data[i]['parent_index'] = parent_index
			bone_data[i]['parent_name'] = parent_name
		for i in range(bone_count):
			x, y, z = struct.unpack('<3f', file.read(3*4))
			bone_data[i]['co'] = mathutils.Vector((x, y, z))
			
			x, y, z = struct.unpack('<3f', file.read(3*4))
			w = struct.unpack('<f', file.read(4))[0]
			bone_data[i]['rot'] = mathutils.Quaternion((w, x, y, z))
		
		vertex_count, mesh_count, local_bone_count = struct.unpack('<3i', file.read(3*4))
		
		# ローカルボーン情報読み込み
		local_bone_data = []
		for i in range(local_bone_count):
			local_bone_data.append({})
			local_bone_data[i]['name'] = ReadStr(file)
		for i in range(local_bone_count):
			row0 = struct.unpack('<4f', file.read(4*4))
			row1 = struct.unpack('<4f', file.read(4*4))
			row2 = struct.unpack('<4f', file.read(4*4))
			row3 = struct.unpack('<4f', file.read(4*4))
			local_bone_data[i]['matrix'] = mathutils.Matrix([row0, row1, row2, row3])
		
		# 頂点情報読み込み
		vertex_data = []
		for i in range(vertex_count):
			vertex_data.append({})
			vertex_data[i]['co'] = struct.unpack('<3f', file.read(3*4))
			vertex_data[i]['normal'] = struct.unpack('<3f', file.read(3*4))
			vertex_data[i]['uv'] = struct.unpack('<2f', file.read(2*4))
		unknown_count = struct.unpack('<i', file.read(4))[0]
		for i in range(unknown_count):
			struct.unpack('<4f', file.read(4*4))
		for i in range(vertex_count):
			vertex_data[i]['weights'] = [{}, {}, {}, {}]
			for j in range(4):
				vertex_data[i]['weights'][j]['index'] = struct.unpack('<H', file.read(2))[0]
				vertex_data[i]['weights'][j]['name'] = local_bone_data[vertex_data[i]['weights'][j]['index']]['name']
			for j in range(4):
				vertex_data[i]['weights'][j]['value'] = struct.unpack('<f', file.read(4))[0]
		
		# 面情報読み込み
		face_data = []
		for i in range(mesh_count):
			face_data.append([])
			face_count = int( struct.unpack('<i', file.read(4))[0] / 3 )
			for j in range(face_count):
				face_data[i].append(struct.unpack('<3h', file.read(3*2)))
		
		# マテリアル情報読み込み
		material_data = []
		material_count = struct.unpack('<i', file.read(4))[0]
		for i in range(material_count):
			material_data.append({})
			material_data[i]['name1'] = ReadStr(file)
			material_data[i]['name2'] = ReadStr(file)
			material_data[i]['name3'] = ReadStr(file)
			material_data[i]['data'] = []
			while True:
				data_type = ReadStr(file)
				if data_type == 'tex':
					material_data[i]['data'].append({'type':data_type})
					material_data[i]['data'][-1]['name'] = ReadStr(file)
					material_data[i]['data'][-1]['type2'] = ReadStr(file)
					if material_data[i]['data'][-1]['type2'] == 'tex2d':
						material_data[i]['data'][-1]['name2'] = ReadStr(file)
						material_data[i]['data'][-1]['path'] = ReadStr(file)
						material_data[i]['data'][-1]['color'] = struct.unpack('<4f', file.read(4*4))
				elif data_type == 'col':
					material_data[i]['data'].append({'type':data_type})
					material_data[i]['data'][-1]['name'] = ReadStr(file)
					material_data[i]['data'][-1]['color'] = struct.unpack('<4f', file.read(4*4))
				elif data_type == 'f':
					material_data[i]['data'].append({'type':data_type})
					material_data[i]['data'][-1]['name'] = ReadStr(file)
					material_data[i]['data'][-1]['float'] = struct.unpack('<f', file.read(4))[0]
				else:
					break
		
		# その他情報読み込み
		misc_data = []
		while True:
			data_type = ReadStr(file)
			if data_type == 'morph':
				misc_data.append({'type':data_type})
				misc_data[-1]['name'] = ReadStr(file)
				morph_vert_count = struct.unpack('<i', file.read(4))[0]
				misc_data[-1]['data'] = []
				for i in range(morph_vert_count):
					misc_data[-1]['data'].append({})
					misc_data[-1]['data'][i]['index'] = struct.unpack('<H', file.read(2))[0]
					misc_data[-1]['data'][i]['co'] = mathutils.Vector(struct.unpack('<3f', file.read(3*4)))
					misc_data[-1]['data'][i]['normal'] = struct.unpack('<3f', file.read(3*4))
			else:
				break
		
		file.close()
		
		try:
			bpy.ops.object.mode_set(mode='OBJECT')
		except RuntimeError:
			pass
		bpy.ops.object.select_all(action='DESELECT')
		
		# アーマチュア作成
		if self.is_armature:
			arm = bpy.data.armatures.new(model_name1 + "." + model_name2 + ".armature")
			arm_ob = bpy.data.objects.new(model_name1 + "." + model_name2 + ".armature", arm)
			bpy.context.scene.objects.link(arm_ob)
			arm_ob.select = True
			bpy.context.scene.objects.active = arm_ob
			bpy.ops.object.mode_set(mode='EDIT')
			
			child_data = []
			for data in bone_data:
				if not data['parent_name']:
					bone = arm.edit_bones.new(ConvertBoneName(data['name'], self.is_convert_bone_names))
					bone.head = (0, 0, 0)
					bone.tail = (0, 0.1, 0)
					
					co = data['co'].copy()
					co.x, co.y, co.z = -co.x, -co.z, co.y
					co *= self.scale
					
					rot = data['rot'].copy()
					
					co_mat = mathutils.Matrix.Translation(co)
					rot_mat = rot.to_matrix().to_4x4()
					bone.matrix = co_mat * rot_mat
					
					if data['unknown']:
						bone.layers[16] = True
						bone.layers[0] = False
				else:
					child_data.append(data)
			
			for i in range(9**9):
				if len(child_data) <= 0:
					break
				data = child_data.pop(0)
				if ConvertBoneName(data['parent_name'], self.is_convert_bone_names) in arm.edit_bones.keys():
					bone = arm.edit_bones.new(ConvertBoneName(data['name'], self.is_convert_bone_names))
					parent = arm.edit_bones[ConvertBoneName(data['parent_name'], self.is_convert_bone_names)]
					bone.parent = parent
					if data['unknown']:
						bone.bbone_segments = 2
					bone.head = (0, 0, 0)
					bone.tail = (0, 0.05, 0)
					
					temp_parent = bone
					co = mathutils.Vector()
					rot = mathutils.Quaternion()
					for j in range(9**9):
						for b in bone_data:
							if ConvertBoneName(b['name'], self.is_convert_bone_names) == temp_parent.name:
								c = b['co'].copy()
								r = b['rot'].copy()
								break
						
						co = r * co
						co += c
						
						rot.rotate(r)
						
						if temp_parent.parent == None:
							break
						temp_parent = temp_parent.parent
					co.x, co.y, co.z = -co.x, -co.z, co.y
					co *= self.scale
					
					co_mat = mathutils.Matrix.Translation(co)
					rot_mat = rot.to_matrix().to_4x4()
					
					bone.matrix = co_mat * rot_mat
					
					if data['unknown']:
						bone.layers[16] = True
						bone.layers[0] = False
				else:
					child_data.append(data)
			
			# ボーン整頓
			if self.is_armature_arrange:
				has_child = []
				# 整頓
				for bone in arm.edit_bones:
					if 1 == len(bone.children):
						bone.tail = bone.children[0].head
						has_child.append(bone.name)
			
			# 一部ボーン削除
			if self.is_armature_clean:
				for bone in arm.edit_bones:
					for b in local_bone_data:
						name = ConvertBoneName(b['name'], self.is_convert_bone_names)
						if bone.name == name:
							break
					else:
						arm.edit_bones.remove(bone)
			
			# ボーン整頓
			if self.is_armature_arrange:
				# 整頓
				for bone in arm.edit_bones:
					if len(bone.children) == 0 and bone.name in has_child:
						pass
					elif 1 == len(bone.children):
						bone.tail = bone.children[0].head
						bone.children[0].use_connect = True
					elif 2 <= len(bone.children):
						total = mathutils.Vector()
						for child in bone.children:
							total += child.head
						bone.tail = total / len(bone.children)
					else:
						if bone.parent:
							v = bone.parent.tail - bone.parent.head
							bone.tail = bone.head + (v * 0.75)
			
			arm.layers[16] = True
			arm.draw_type = 'STICK'
			arm_ob.show_x_ray = True
			bpy.ops.object.mode_set(mode='OBJECT')
			#arm_ob.scale *= self.scale
		
		if self.is_mesh:
			# メッシュ作成
			me = context.blend_data.meshes.new(model_name1 + "." + model_name2)
			verts, faces = [], []
			for data in vertex_data:
				co = list(data['co'][:])
				co[0] = -co[0]
				co[0] *= self.scale
				co[1] *= self.scale
				co[2] *= self.scale
				verts.append(co)
			for data in face_data:
				faces.extend(data)
			me.from_pydata(verts, [], faces)
			# オブジェクト化
			ob = context.blend_data.objects.new(model_name1 + "." + model_name2, me)
			context.scene.objects.link(ob)
			ob.select = True
			context.scene.objects.active = ob
			bpy.ops.object.shade_smooth()
			# オブジェクト変形
			for bone in bone_data:
				if bone['name'] == model_name2:
					co = bone['co'].copy()
					co.x, co.y, co.z = -co.x, -co.z, co.y
					co *= self.scale
					ob.location = co
					
					rot = bone['rot'].copy()
					eul = mathutils.Euler((math.radians(90), 0, 0), 'XYZ')
					rot.rotate(eul)
					ob.rotation_mode = 'QUATERNION'
					ob.rotation_quaternion = rot
					
					break
			#ob.scale *= self.scale
			
			# 頂点グループ作成
			for data in local_bone_data:
				ob.vertex_groups.new(ConvertBoneName(data['name'], self.is_convert_vertex_group_names))
			for vert_index, data in enumerate(vertex_data):
				for weight in data['weights']:
					if 0.0 < weight['value']:
						vertex_group = ob.vertex_groups[ConvertBoneName(weight['name'], self.is_convert_vertex_group_names)]
						vertex_group.add([vert_index], weight['value'], 'REPLACE')
			if self.is_vertex_group_sort:
				bpy.ops.object.vertex_group_sort(sort_type='NAME')
			if self.is_remove_empty_vertex_group:
				for vg in ob.vertex_groups[:]:
					for vert in me.vertices:
						for group in vert.groups:
							if group.group == vg.index:
								if 0.0 < group.weight:
									break
						else:
							continue
						break
					else:
						ob.vertex_groups.remove(vg)
			# UV作成
			me.uv_textures.new("UVMap")
			bm = bmesh.new()
			bm.from_mesh(me)
			for face in bm.faces:
				for loop in face.loops:
					loop[bm.loops.layers.uv.active].uv = vertex_data[loop.vert.index]['uv']
			bm.to_mesh(me)
			bm.free()
			# モーフ追加
			ob.shape_key_add(name="Basis", from_mix=False)
			for data in misc_data:
				if data['type'] == 'morph':
					shape_key = ob.shape_key_add(name=data['name'], from_mix=False)
					for vert in data['data']:
						co = vert['co']
						co.x = -co.x
						co *= self.scale
						shape_key.data[vert['index']].co = shape_key.data[vert['index']].co + co
			
			# マテリアル追加
			face_seek = 0
			for index, data in enumerate(material_data):
				override = context.copy()
				override['object'] = ob
				bpy.ops.object.material_slot_add(override)
				mate = context.blend_data.materials.new(data['name1'])
				mate['shader1'] = data['name2']
				mate['shader2'] = data['name3']
				ob.material_slots[-1].material = mate
				# 面にマテリアル割り当て
				for i in range(face_seek, face_seek + len(face_data[index])):
					me.polygons[i].material_index = index
				face_seek += len(face_data[index])
				# テクスチャ追加
				for tex_index, tex_data in enumerate(data['data']):
					if tex_data['type'] == 'tex':
						slot = mate.texture_slots.create(tex_index)
						tex = context.blend_data.textures.new(tex_data['name'], 'IMAGE')
						slot.texture = tex
						if tex_data['type2'] == 'tex2d':
							#slot.use_map_color_diffuse = False
							slot.color = tex_data['color'][:3]
							slot.diffuse_color_factor = tex_data['color'][3]
							img = context.blend_data.images.new(tex_data['name2'], 128, 128)
							img.filepath = tex_data['path']
							img.source = 'FILE'
							tex.image = img
					elif tex_data['type'] == 'col':
						slot = mate.texture_slots.create(tex_index)
						mate.use_textures[tex_index] = False
						#slot.use_map_color_diffuse = False
						slot.color = tex_data['color'][:3]
						slot.diffuse_color_factor = tex_data['color'][3]
						slot.use_rgb_to_intensity = True
						tex = context.blend_data.textures.new(tex_data['name'], 'IMAGE')
						slot.texture = tex
						if tex_data['name'] == "_RimColor" and self.is_mate_color:
							mate.diffuse_color = tex_data['color'][:3]
							mate.diffuse_color.v += 0.5
					elif tex_data['type'] == 'f':
						slot = mate.texture_slots.create(tex_index)
						mate.use_textures[tex_index] = False
						#slot.use_map_color_diffuse = False
						slot.diffuse_color_factor = tex_data['float']
						tex = context.blend_data.textures.new(tex_data['name'], 'IMAGE')
						slot.texture = tex
			
			# メッシュ整頓
			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.mesh.select_all(action='SELECT')
			bpy.ops.mesh.flip_normals()
			bpy.ops.mesh.select_all(action='DESELECT')
			bpy.ops.object.mode_set(mode='OBJECT')
			if self.is_remove_doubles:
				comparison_data = []
				for data in vertex_data:
					comparison_data.append((data['co'], data['normal']))
				for i, vert in enumerate(me.vertices):
					if 2 <= comparison_data.count(comparison_data[i]):
						vert.select = True
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.remove_doubles(threshold=0.000001)
				bpy.ops.object.mode_set(mode='OBJECT')
			if self.is_seam:
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.select_all(action='SELECT')
				bpy.ops.uv.seams_from_islands()
				bpy.ops.object.mode_set(mode='OBJECT')
			
			if self.is_armature:
				mod = ob.modifiers.new("Armature", 'ARMATURE')
				mod.object = arm_ob
				context.scene.objects.active = arm_ob
				bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
				context.scene.objects.active = ob
		
		# マテリアル情報のテキスト埋め込み
		if self.is_mate_data_text:
			for index, data in enumerate(material_data):
				txt_name = "Material:" + str(index)
				if txt_name in context.blend_data.texts.keys():
					txt = context.blend_data.texts[txt_name]
					txt.clear()
				else:
					txt = context.blend_data.texts.new(txt_name)
				txt.write("***\n")
				txt.write("***\n")
				txt.write(data['name1'] + "\n")
				txt.write(data['name2'] + "\n")
				txt.write(data['name3'] + "\n")
				txt.write("\n")
				for tex_data in data['data']:
					txt.write(tex_data['type'] + "\n")
					if tex_data['type'] == 'tex':
						txt.write("\t" + tex_data['name'] + "\n")
						txt.write("\t" + tex_data['type2'] + "\n")
						if tex_data['type2'] == 'tex2d':
							txt.write("\t" + tex_data['name2'] + "\n")
							txt.write("\t" + tex_data['path'] + "\n")
							col = str(tex_data['color'][0]) + " " + str(tex_data['color'][1]) + " " + str(tex_data['color'][2]) + " " + str(tex_data['color'][3])
							txt.write("\t" + col + "\n")
					elif tex_data['type'] == 'col':
						txt.write("\t" + tex_data['name'] + "\n")
						col = str(tex_data['color'][0]) + " " + str(tex_data['color'][1]) + " " + str(tex_data['color'][2]) + " " + str(tex_data['color'][3])
						txt.write("\t" + col + "\n")
					elif tex_data['type'] == 'f':
						txt.write("\t" + tex_data['name'] + "\n")
						txt.write("\t" + str(tex_data['float']) + "\n")
		
		# ボーン情報のテキスト埋め込み
		if self.is_bone_data_text:
			if "BoneData" in context.blend_data.texts.keys():
				txt = context.blend_data.texts["BoneData"]
				txt.clear()
				self.report(type={'INFO'}, message="テキスト「BoneData」が上書きされました")
			else:
				txt = context.blend_data.texts.new("BoneData")
		for i, data in enumerate(bone_data):
			s = data['name'] + ","
			s = s + str(data['unknown']) + ","
			parent_index = data['parent_index']
			if -1 < parent_index:
				s = s + bone_data[parent_index]['name'] + ","
			else:
				s = s + "None" + ","
			s = s + str(data['co'][0]) + " "
			s = s + str(data['co'][1]) + " "
			s = s + str(data['co'][2]) + ","
			s = s + str(data['rot'][0]) + " "
			s = s + str(data['rot'][1]) + " "
			s = s + str(data['rot'][2]) + " "
			s = s + str(data['rot'][3])
			
			if self.is_bone_data_text:
				txt.write(s + "\n")
			if self.is_bone_data_obj_property:
				ob["BoneData:" + str(i)] = s
			if self.is_armature and self.is_bone_data_arm_property:
				arm["BoneData:" + str(i)] = s
		
		# ローカルボーン情報のテキスト埋め込み
		if self.is_bone_data_text:
			if "LocalBoneData" in context.blend_data.texts.keys():
				txt = context.blend_data.texts["LocalBoneData"]
				txt.clear()
				self.report(type={'INFO'}, message="テキスト「LocalBoneData」が上書きされました")
			else:
				txt = context.blend_data.texts.new("LocalBoneData")
		for i, data in enumerate(local_bone_data):
			s = data['name'] + ","
			
			s = s + str(data['matrix'][0][0]) + " "
			s = s + str(data['matrix'][0][1]) + " "
			s = s + str(data['matrix'][0][2]) + " "
			s = s + str(data['matrix'][0][3]) + " "
			
			s = s + str(data['matrix'][1][0]) + " "
			s = s + str(data['matrix'][1][1]) + " "
			s = s + str(data['matrix'][1][2]) + " "
			s = s + str(data['matrix'][1][3]) + " "
			
			s = s + str(data['matrix'][2][0]) + " "
			s = s + str(data['matrix'][2][1]) + " "
			s = s + str(data['matrix'][2][2]) + " "
			s = s + str(data['matrix'][2][3]) + " "
			
			s = s + str(data['matrix'][3][0]) + " "
			s = s + str(data['matrix'][3][1]) + " "
			s = s + str(data['matrix'][3][2]) + " "
			s = s + str(data['matrix'][3][3])
			
			if self.is_bone_data_text:
				txt.write(s + "\n")
			if self.is_bone_data_obj_property:
				ob["LocalBoneData:" + str(i)] = s
			if self.is_armature and self.is_bone_data_arm_property:
				arm["LocalBoneData:" + str(i)] = s
		
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(import_cm3d2_model.bl_idname, icon='SPACE2')
