import bmesh
import bpy
import math
import mathutils
import struct
import time
from collections import Counter
from . import common

# メインオペレーター
class import_cm3d2_model(bpy.types.Operator):
	bl_idname = 'import_mesh.import_cm3d2_model'
	bl_label = "CM3D2モデル (.model)"
	bl_description = "カスタムメイド3D2のmodelファイルを読み込みます"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".model"
	filter_glob = bpy.props.StringProperty(default="*.model", options={'HIDDEN'})
	
	scale = bpy.props.FloatProperty(name="倍率", default=5, min=0.1, max=100, soft_min=0.1, soft_max=100, step=100, precision=1, description="インポート時のメッシュ等の拡大率です")
	
	is_mesh = bpy.props.BoolProperty(name="メッシュ生成", default=True, description="ポリゴンを読み込みます、大抵の場合オンでOKです")
	is_remove_doubles = bpy.props.BoolProperty(name="重複頂点を結合", default=True, description="UVの切れ目でポリゴンが分かれている仕様なので、インポート時にくっつけます")
	is_seam = bpy.props.BoolProperty(name="シームをつける", default=True, description="UVの切れ目にシームをつけます")
	
	is_convert_bone_weight_names = bpy.props.BoolProperty(name="頂点グループ名をBlender用に変換", default=False, description="全ての頂点グループ名をBlenderの左右対称編集で使えるように変換してから読み込みます")
	is_vertex_group_sort = bpy.props.BoolProperty(name="頂点グループを名前順ソート", default=True, description="頂点グループを名前順でソートします")
	is_remove_empty_vertex_group = bpy.props.BoolProperty(name="割り当てのない頂点グループを削除", default=True, description="全ての頂点に割り当てのない頂点グループを削除します")
	
	is_replace_cm3d2_tex = bpy.props.BoolProperty(name="テクスチャを探す", default=True, description="CM3D2本体のインストールフォルダからtexファイルを探して開きます")
	is_decorate = bpy.props.BoolProperty(name="種類に合わせてマテリアルを装飾", default=True)
	is_mate_data_text = bpy.props.BoolProperty(name="テキストにマテリアル情報埋め込み", default=True, description="シェーダー情報をテキストに埋め込みます")
	
	is_armature = bpy.props.BoolProperty(name="アーマチュア生成", default=True, description="ウェイトを編集する時に役立つアーマチュアを読み込みます")
	is_armature_clean = bpy.props.BoolProperty(name="不要なボーンを削除", default=False, description="ウェイトが無いボーンを削除します")
	
	is_bone_data_text = bpy.props.BoolProperty(name="テキスト", default=True, description="ボーン情報をテキストとして読み込みます")
	is_bone_data_obj_property = bpy.props.BoolProperty(name="オブジェクトのカスタムプロパティ", default=True, description="メッシュオブジェクトのカスタムプロパティにボーン情報を埋め込みます")
	is_bone_data_arm_property = bpy.props.BoolProperty(name="アーマチュアのカスタムプロパティ", default=True, description="アーマチュアデータのカスタムプロパティにボーン情報を埋め込みます")
	
	def invoke(self, context, event):
		if common.preferences().model_default_path:
			self.filepath = common.default_cm3d2_dir(common.preferences().model_default_path, "", "model")
		else:
			self.filepath = common.default_cm3d2_dir(common.preferences().model_import_path, "", "model")
		self.scale = common.preferences().scale
		self.is_replace_cm3d2_tex = common.preferences().is_replace_cm3d2_tex
		self.is_convert_bone_weight_names = common.preferences().is_convert_bone_weight_names
		context.window_manager.fileselect_add(self)
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
		sub_box.prop(self, 'is_vertex_group_sort', icon='SORTALPHA')
		sub_box.prop(self, 'is_remove_empty_vertex_group', icon='DISCLOSURE_TRI_DOWN')
		sub_box.prop(self, 'is_convert_bone_weight_names', icon='BLENDER')
		sub_box = box.box()
		sub_box.label("マテリアル")
		sub_box.prop(self, 'is_replace_cm3d2_tex', icon='BORDERMOVE')
		sub_box.prop(self, 'is_decorate', icon='TEXTURE_SHADED')
		sub_box.prop(self, 'is_mate_data_text', icon='TEXT')
		box = self.layout.box()
		box.prop(self, 'is_armature', icon='ARMATURE_DATA')
		sub_box = box.box()
		sub_box.label("アーマチュア")
		sub_box.prop(self, 'is_armature_clean', icon='X')
		sub_box.prop(self, 'is_convert_bone_weight_names', icon='BLENDER', text="ボーン名をBlender用に変換")
		box = self.layout.box()
		box.label("ボーン情報埋め込み場所")
		box.prop(self, 'is_bone_data_text', icon='TEXT')
		box.prop(self, 'is_bone_data_obj_property', icon='OBJECT_DATA')
		box.prop(self, 'is_bone_data_arm_property', icon='ARMATURE_DATA')
	
	def execute(self, context):
		start_time = time.time()
		
		common.preferences().model_import_path = self.filepath
		common.preferences().scale = self.scale
		context.window_manager.progress_begin(0, 10)
		context.window_manager.progress_update(0)
		
		try:
			file = open(self.filepath, 'rb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可かファイルが存在しません")
			return {'CANCELLED'}
		
		# ヘッダー
		ext = common.read_str(file)
		if ext != 'CM3D2_MESH':
			self.report(type={'ERROR'}, message="これはカスタムメイド3D2のモデルファイルではありません")
			return {'CANCELLED'}
		struct.unpack('<i', file.read(4))[0]
		context.window_manager.progress_update(0.1)
		
		# 名前群を取得
		model_name1 = common.read_str(file)
		model_name2 = common.read_str(file)
		context.window_manager.progress_update(0.2)
		
		# ボーン情報読み込み
		bone_data = []
		bone_count = struct.unpack('<i', file.read(4))[0]
		for i in range(bone_count):
			bone_data.append({})
			bone_data[i]['name'] = common.read_str(file)
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
		context.window_manager.progress_update(0.3)
		
		vertex_count, mesh_count, local_bone_count = struct.unpack('<3i', file.read(3*4))
		
		# ローカルボーン情報読み込み
		local_bone_data = []
		for i in range(local_bone_count):
			local_bone_data.append({})
			local_bone_data[i]['name'] = common.read_str(file)
		for i in range(local_bone_count):
			row0 = struct.unpack('<4f', file.read(4*4))
			row1 = struct.unpack('<4f', file.read(4*4))
			row2 = struct.unpack('<4f', file.read(4*4))
			row3 = struct.unpack('<4f', file.read(4*4))
			local_bone_data[i]['matrix'] = mathutils.Matrix([row0, row1, row2, row3])
		context.window_manager.progress_update(0.4)
		
		# 頂点情報読み込み
		vertex_data = []
		for i in range(vertex_count):
			co = struct.unpack('<3f', file.read(3*4))
			no = struct.unpack('<3f', file.read(3*4))
			uv = struct.unpack('<2f', file.read(2*4))
			vertex_data.append({'co': co, 'normal': no, 'uv': uv})
		comparison_data = list(hash(repr(v['co'] + v['normal'])) for v in vertex_data)
		comparison_counter = Counter(comparison_data)
		comparison_data = list((comparison_counter[h] > 1) for h in comparison_data)
		del comparison_counter
		unknown_count = struct.unpack('<i', file.read(4))[0]
		for i in range(unknown_count):
			struct.unpack('<4f', file.read(4*4))
		for i in range(vertex_count):
			indexes = struct.unpack('<4H', file.read(4*2))
			values  = struct.unpack('<4f', file.read(4*4))
			vertex_data[i]['weights'] = list({
					'index': index,
					'value': value,
					'name': local_bone_data[index]['name'],
				} for index, value in zip(indexes, values))
		context.window_manager.progress_update(0.5)
		
		# 面情報読み込み
		face_data = []
		for i in range(mesh_count):
			face_count = int(struct.unpack('<i', file.read(4))[0] / 3)
			face_data.append([tuple(reversed(struct.unpack('<3H', file.read(3*2)))) for j in range(face_count)])
		context.window_manager.progress_update(0.6)
		
		# マテリアル情報読み込み
		material_data = []
		material_count = struct.unpack('<i', file.read(4))[0]
		for i in range(material_count):
			material_data.append({})
			material_data[i]['name1'] = common.read_str(file)
			material_data[i]['name2'] = common.read_str(file)
			material_data[i]['name3'] = common.read_str(file)
			material_data[i]['data'] = []
			while True:
				data_type = common.read_str(file)
				if data_type == 'tex':
					material_data[i]['data'].append({'type':data_type})
					material_data[i]['data'][-1]['name'] = common.read_str(file)
					material_data[i]['data'][-1]['type2'] = common.read_str(file)
					if material_data[i]['data'][-1]['type2'] == 'tex2d':
						material_data[i]['data'][-1]['name2'] = common.read_str(file)
						material_data[i]['data'][-1]['path'] = common.read_str(file)
						material_data[i]['data'][-1]['color'] = struct.unpack('<4f', file.read(4*4))
				elif data_type == 'col':
					material_data[i]['data'].append({'type':data_type})
					material_data[i]['data'][-1]['name'] = common.read_str(file)
					material_data[i]['data'][-1]['color'] = struct.unpack('<4f', file.read(4*4))
				elif data_type == 'f':
					material_data[i]['data'].append({'type':data_type})
					material_data[i]['data'][-1]['name'] = common.read_str(file)
					material_data[i]['data'][-1]['float'] = struct.unpack('<f', file.read(4))[0]
				else:
					break
		context.window_manager.progress_update(0.8)
		
		# その他情報読み込み
		misc_data = []
		while True:
			data_type = common.read_str(file)
			if data_type == 'morph':
				misc_data.append({'type':data_type})
				misc_data[-1]['name'] = common.read_str(file)
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
		context.window_manager.progress_update(1)
		
		try:
			bpy.ops.object.mode_set(mode='OBJECT')
		except RuntimeError:
			pass
		bpy.ops.object.select_all(action='DESELECT')
		
		# アーマチュア作成
		if self.is_armature:
			arm = bpy.data.armatures.new(model_name1 + ".armature")
			arm_ob = bpy.data.objects.new(model_name1 + ".armature", arm)
			bpy.context.scene.objects.link(arm_ob)
			arm_ob.select = True
			bpy.context.scene.objects.active = arm_ob
			bpy.ops.object.mode_set(mode='EDIT')
			
			child_data = []
			for data in bone_data:
				if not data['parent_name']:
					bone = arm.edit_bones.new(common.decode_bone_name(data['name'], self.is_convert_bone_weight_names))
					bone.head = (0, 0, 0)
					bone.tail = (0, 1, 0)
					
					co = data['co'].copy()
					co.x, co.y, co.z = -co.x, -co.z, co.y
					co *= self.scale
					
					rot = mathutils.Euler((0, math.radians(0), 0)).to_quaternion()
					rot = rot * data['rot'].copy()
					rot.x, rot.y, rot.z, rot.w = -rot.x, -rot.z, rot.y, -rot.w
					q = mathutils.Quaternion((0, 0, 1), math.radians(-90))
					rot = rot * q
					
					co_mat = mathutils.Matrix.Translation(co)
					rot_mat = rot.to_matrix().to_4x4()
					bone.matrix = co_mat * rot_mat
					
					co = bone.tail - bone.head
					#co.x, co.y, co.z = -co.y, co.x, co.z
					#bone.tail = bone.head + co
					
					if data['unknown']:
						bone.layers[16] = True
						bone.layers[0] = False
				else:
					child_data.append(data)
			context.window_manager.progress_update(1.2)
			
			for i in range(9**9):
				if len(child_data) <= 0:
					break
				data = child_data.pop(0)
				if common.decode_bone_name(data['parent_name'], self.is_convert_bone_weight_names) in arm.edit_bones:
					bone = arm.edit_bones.new(common.decode_bone_name(data['name'], self.is_convert_bone_weight_names))
					parent = arm.edit_bones[common.decode_bone_name(data['parent_name'], self.is_convert_bone_weight_names)]
					bone.parent = parent
					if data['unknown']:
						bone.bbone_segments = 2
					bone.head = (0, 0, 0)
					bone.tail = (0, 1, 0)
					
					rots = []
					temp_parent = bone
					co = mathutils.Vector()
					rot = mathutils.Euler((0, math.radians(0), 0)).to_quaternion()
					for j in range(9**9):
						for b in bone_data:
							if common.decode_bone_name(b['name'], self.is_convert_bone_weight_names) == temp_parent.name:
								c = b['co'].copy()
								r = b['rot'].copy()
								break
						
						co = r * co
						co += c
						
						r.x, r.y, r.z, r.w = -r.x, -r.z, r.y, -r.w
						rots.append(r.copy())
						
						if temp_parent.parent == None:
							break
						temp_parent = temp_parent.parent
					co.x, co.y, co.z = -co.x, -co.z, co.y
					co *= self.scale
					
					rots.reverse()
					rot = mathutils.Euler((0, math.radians(0), 0)).to_quaternion()
					for r in rots:
						rot = rot * r
					q = mathutils.Quaternion((0, 0, 1), math.radians(-90))
					rot = rot * q
					
					co_mat = mathutils.Matrix.Translation(co)
					rot_mat = rot.to_matrix().to_4x4()
					
					bone.matrix = co_mat * rot_mat
					
					if data['unknown']:
						bone.layers[16] = True
						bone.layers[0] = False
				else:
					child_data.append(data)
			context.window_manager.progress_update(1.3)
			
			# ボーン整頓
			for bone in arm.edit_bones:
				if len(bone.children) == 0:
					if bone.parent:
						pass
					else:
						bone.length = 1.0
				elif len(bone.children) == 1:
					co = bone.children[0].head - bone.head
					bone.length = co.length
				elif len(bone.children) >= 2:
					max_len = 0.0
					for child_bone in bone.children:
						co = child_bone.head - bone.head
						if max_len < co.length:
							max_len = co.length
					bone.length = max_len
					if bone.name == "Bip01":
						bone.length = 1.0
			for bone in arm.edit_bones:
				if len(bone.children) == 0:
					if bone.parent:
						bone.length = bone.parent.length * 0.5
			
			# 一部ボーン削除
			if self.is_armature_clean:
				for bone in arm.edit_bones:
					for b in local_bone_data:
						name = common.decode_bone_name(b['name'], self.is_convert_bone_weight_names)
						if bone.name == name:
							break
					else:
						arm.edit_bones.remove(bone)
			
			arm.layers[16] = True
			arm.draw_type = 'STICK'
			arm_ob.show_x_ray = True
			bpy.ops.armature.select_all(action='DESELECT')
			bpy.ops.object.mode_set(mode='OBJECT')
		context.window_manager.progress_update(2)
		
		if self.is_mesh:
			# メッシュ作成
			me = context.blend_data.meshes.new(model_name1)
			verts, faces = [], []
			for data in vertex_data:
				co = list(data['co'][:])
				co[0] = -co[0]
				co[0] *= self.scale
				co[1] *= self.scale
				co[2] *= self.scale
				verts.append(co)
			context.window_manager.progress_update(2.2)
			for data in face_data:
				faces.extend(data)
			context.window_manager.progress_update(2.5)
			me.from_pydata(verts, [], faces)
			# オブジェクト化
			ob = context.blend_data.objects.new(model_name1, me)
			context.scene.objects.link(ob)
			ob.select = True
			context.scene.objects.active = ob
			bpy.ops.object.shade_smooth()
			context.window_manager.progress_update(2.7)
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
			context.window_manager.progress_update(3)
			
			# 頂点グループ作成
			for data in local_bone_data:
				ob.vertex_groups.new(common.decode_bone_name(data['name'], self.is_convert_bone_weight_names))
			context.window_manager.progress_update(3.3)
			for vert_index, data in enumerate(vertex_data):
				for weight in data['weights']:
					if 0.0 < weight['value']:
						vertex_group = ob.vertex_groups[common.decode_bone_name(weight['name'], self.is_convert_bone_weight_names)]
						vertex_group.add([vert_index], weight['value'], 'REPLACE')
			context.window_manager.progress_update(3.7)
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
			ob.vertex_groups.active_index = 0
			context.window_manager.progress_update(4)
			
			# UV作成
			bpy.ops.mesh.uv_texture_add()
			bm = bmesh.new()
			bm.from_mesh(me)
			for face in bm.faces:
				for loop in face.loops:
					loop[bm.loops.layers.uv.active].uv = vertex_data[loop.vert.index]['uv']
			bm.to_mesh(me)
			bm.free()
			context.window_manager.progress_update(5)
			
			# モーフ追加
			morph_count = 0
			for data in misc_data:
				if data['type'] == 'morph':
					if morph_count == 0:
						bpy.ops.object.shape_key_add(from_mix=False)
						me.shape_keys.name = model_name1
					shape_key = ob.shape_key_add(name=data['name'], from_mix=False)
					for vert in data['data']:
						co = vert['co']
						co.x = -co.x
						co *= self.scale
						shape_key.data[vert['index']].co = shape_key.data[vert['index']].co + co
					morph_count += 1
			context.window_manager.progress_update(6)
			
			# マテリアル追加
			progress_count_total = 0.0
			for data in material_data:
				progress_count_total += len(data['data'])
			progress_plus_value = 1.0 / progress_count_total
			progress_count = 6.0
			
			tex_storage_files = common.get_tex_storage_files()
			
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
				already_texs = []
				tex_index = 0
				for tex_data in data['data']:
					
					if common.preferences().mate_unread_same_value:
						if tex_data['name'] in already_texs:
							continue
						already_texs.append(tex_data['name'])
					
					if tex_data['type'] == 'tex':
						slot = mate.texture_slots.create(tex_index)
						tex = context.blend_data.textures.new(tex_data['name'], 'IMAGE')
						slot.texture = tex
						if tex_data['type2'] == 'tex2d':
							slot.color = tex_data['color'][:3]
							slot.diffuse_color_factor = tex_data['color'][3]
							img = context.blend_data.images.new(tex_data['name2'], 128, 128)
							img.filepath = tex_data['path']
							img['cm3d2_path'] = tex_data['path']
							img.source = 'FILE'
							tex.image = img
							
							# tex探し
							if self.is_replace_cm3d2_tex:
								if common.replace_cm3d2_tex(img, tex_storage_files) and tex_data['name']=='_MainTex':
									for face in me.polygons:
										if face.material_index == index:
											me.uv_textures.active.data[face.index].image = img
					
					elif tex_data['type'] == 'col':
						slot = mate.texture_slots.create(tex_index)
						mate.use_textures[tex_index] = False
						slot.color = tex_data['color'][:3]
						slot.diffuse_color_factor = tex_data['color'][3]
						slot.use_rgb_to_intensity = True
						tex = context.blend_data.textures.new(tex_data['name'], 'BLEND')
						slot.texture = tex
					
					elif tex_data['type'] == 'f':
						slot = mate.texture_slots.create(tex_index)
						mate.use_textures[tex_index] = False
						slot.diffuse_color_factor = tex_data['float']
						tex = context.blend_data.textures.new(tex_data['name'], 'BLEND')
						slot.texture = tex
					
					tex_index += 1
					
					progress_count += progress_plus_value
					context.window_manager.progress_update(progress_count)
				common.decorate_material(mate, self.is_decorate, me, index)
			ob.active_material_index = 0
			context.window_manager.progress_update(7)
			
			# メッシュ整頓
			if self.is_remove_doubles:
				for is_comparison, vert in zip(comparison_data, me.vertices):
					if is_comparison:
						vert.select = True
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.remove_doubles(threshold=0.000001)
				bpy.ops.object.mode_set(mode='OBJECT')
			if self.is_seam:
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.select_all(action='SELECT')
				bpy.ops.uv.seams_from_islands()
				bpy.ops.object.mode_set(mode='OBJECT')
			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.mesh.select_all(action='DESELECT')
			bpy.ops.object.mode_set(mode='OBJECT')
			
			if self.is_armature:
				mod = ob.modifiers.new("Armature", 'ARMATURE')
				mod.object = arm_ob
				context.scene.objects.active = arm_ob
				bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
				context.scene.objects.active = ob
		context.window_manager.progress_update(8)
		
		# マテリアル情報のテキスト埋め込み
		if self.is_mate_data_text:
			for index, data in enumerate(material_data):
				txt_name = "Material:" + str(index)
				if txt_name in context.blend_data.texts:
					txt = context.blend_data.texts[txt_name]
					txt.clear()
				else:
					txt = context.blend_data.texts.new(txt_name)
				txt.write("1000" + "\n")
				txt.write(data['name1'].lower() + "\n")
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
							col = " ".join([str(tex_data['color'][0]), str(tex_data['color'][1]), str(tex_data['color'][2]), str(tex_data['color'][3])])
							txt.write("\t" + col + "\n")
					elif tex_data['type'] == 'col':
						txt.write("\t" + tex_data['name'] + "\n")
						col = " ".join([str(tex_data['color'][0]), str(tex_data['color'][1]), str(tex_data['color'][2]), str(tex_data['color'][3])])
						txt.write("\t" + col + "\n")
					elif tex_data['type'] == 'f':
						txt.write("\t" + tex_data['name'] + "\n")
						txt.write("\t" + str(tex_data['float']) + "\n")
				txt.current_line_index = 0
		context.window_manager.progress_update(9)
		
		# ボーン情報のテキスト埋め込み
		if self.is_bone_data_text:
			if "BoneData" in context.blend_data.texts:
				txt = context.blend_data.texts["BoneData"]
				txt.clear()
			else:
				txt = context.blend_data.texts.new("BoneData")
		for i, data in enumerate(bone_data):
			s = ",".join([data['name'], str(data['unknown']), ""])
			parent_index = data['parent_index']
			if -1 < parent_index:
				s += bone_data[parent_index]['name'] + ","
			else:
				s += "None" + ","
			s += " ".join([str(data['co'][0]), str(data['co'][1]), str(data['co'][2])]) + ","
			s += " ".join([str(data['rot'][0]), str(data['rot'][1]), str(data['rot'][2]), str(data['rot'][3])])
			
			if self.is_bone_data_text:
				txt.write(s + "\n")
			if self.is_mesh and self.is_bone_data_obj_property:
				ob["BoneData:" + str(i)] = s
			if self.is_armature and self.is_bone_data_arm_property:
				arm["BoneData:" + str(i)] = s
		if self.is_bone_data_text:
			txt['BaseBone'] = model_name2
			txt.current_line_index = 0
		context.window_manager.progress_update(10)
		
		# ローカルボーン情報のテキスト埋め込み
		if self.is_bone_data_text:
			if "LocalBoneData" in context.blend_data.texts:
				txt = context.blend_data.texts["LocalBoneData"]
				txt.clear()
			else:
				txt = context.blend_data.texts.new("LocalBoneData")
		for i, data in enumerate(local_bone_data):
			s = data['name'] + ","
			
			mat_list = list(data['matrix'][0])
			mat_list.extend(list(data['matrix'][1]))
			mat_list.extend(list(data['matrix'][2]))
			mat_list.extend(list(data['matrix'][3]))
			for j, f in enumerate(mat_list):
				mat_list[j] = str(f)
			s += " ".join(mat_list)
			
			if self.is_bone_data_text:
				txt.write(s + "\n")
			if self.is_mesh and self.is_bone_data_obj_property:
				ob["LocalBoneData:" + str(i)] = s
			if self.is_armature and self.is_bone_data_arm_property:
				arm["LocalBoneData:" + str(i)] = s
		if self.is_bone_data_text:
			txt['BaseBone'] = model_name2
			txt.current_line_index = 0
		
		if self.is_mesh and self.is_bone_data_obj_property:
			ob['BaseBone'] = model_name2
		if self.is_armature and self.is_bone_data_arm_property:
			arm['BaseBone'] = model_name2
		
		context.window_manager.progress_end()
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		self.report(type={'INFO'}, message="modelのインポートが完了しました")
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(import_cm3d2_model.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
