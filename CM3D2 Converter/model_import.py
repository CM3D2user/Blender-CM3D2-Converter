# modelファイルのインポーター
import bpy, struct, mathutils

def ReadStr(file):
	str_index = struct.unpack('<B', file.read(1))[0]
	if 128 <= str_index:
		i = struct.unpack('<B', file.read(1))[0]
		str_index += (i * 128) - 128
	return file.read(str_index).decode('utf-8')

# メインオペレーター
class import_cm3d2_model(bpy.types.Operator):
	bl_idname = "import_mesh.import_cm3d2_model"
	bl_label = "CM3D2 Model (.model)"
	bl_description = "カスタムメイド3D2のmodelファイルを読み込みます"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath = bpy.props.StringProperty(subtype="FILE_PATH")
	
	def invoke(self, context, event):
		self.filepath = context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.model_import_path = self.filepath
		
		file = open(self.filepath, 'rb')
		
		# ヘッダー
		ReadStr(file)
		struct.unpack('<i', file.read(4))[0]
		
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
			
			w = struct.unpack('<f', file.read(4))[0]
			x, y, z = struct.unpack('<3f', file.read(3*4))
			bone_data[i]['rot'] = mathutils.Quaternion((x, y, z), w)
		
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
		struct.unpack('<i', file.read(4))[0]
		for i in range(vertex_count):
			vertex_data[i]['weights'] = [{}, {}, {}, {}]
			for j in range(4):
				vertex_data[i]['weights'][j]['index'] = struct.unpack('<h', file.read(2))[0]
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
					if material_data[i]['data'][-1]['type2'] != 'null':
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
					misc_data[-1]['data'][i]['index'] = struct.unpack('<h', file.read(2))[0]
					misc_data[-1]['data'][i]['co'] = struct.unpack('<3f', file.read(3*4))
					misc_data[-1]['data'][i]['normal'] = struct.unpack('<3f', file.read(3*4))
			else:
				break
		
		bpy.ops.object.select_all(action='DESELECT')
		
		# メッシュ作成
		me = context.blend_data.meshes.new(model_name1)
		verts, faces = [], []
		for data in vertex_data:
			verts.append(data['co'])
		for data in face_data:
			faces.extend(data)
		me.from_pydata(verts, [], faces)
		ob = context.blend_data.objects.new(model_name1, me)
		context.scene.objects.link(ob)
		ob.select = True
		context.scene.objects.active = ob
		bpy.ops.object.shade_smooth()
		for data in local_bone_data:
			ob.vertex_groups.new(data['name'])
		for vert_index, data in enumerate(vertex_data):
			for weight in data['weights']:
				if 0.0 < weight['value']:
					vertex_group = ob.vertex_groups[weight['name']]
					vertex_group.add([vert_index], weight['value'], 'REPLACE')
		
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(import_cm3d2_model.bl_idname, icon='PLUGIN')
