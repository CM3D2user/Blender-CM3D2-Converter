import bpy, bmesh, mathutils

class vertex_group_transfer(bpy.types.Operator):
	bl_idname = "object.vertex_group_transfer"
	bl_label = "クイック・ウェイト転送"
	bl_description = "アクティブなメッシュに他の選択メッシュの頂点グループを転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	vertex_group_remove_all = bpy.props.BoolProperty(name="最初に頂点グループ全削除", default=True)
	vertex_group_clean = bpy.props.BoolProperty(name="頂点グループのクリーン", default=True)
	vertex_group_delete = bpy.props.BoolProperty(name="割り当ての無い頂点グループ削除", default=True)
	
	@classmethod
	def poll(cls, context):
		if (len(context.selected_objects) <= 1):
			return False
		source_objs = []
		for obj in context.selected_objects:
			if (obj.type == 'MESH' and context.object.name != obj.name):
				source_objs.append(obj)
		if (len(source_objs) <= 0):
			return False
		for obj in source_objs:
			if (1 <= len(obj.vertex_groups)):
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'vertex_group_remove_all')
		self.layout.prop(self, 'vertex_group_clean')
		self.layout.prop(self, 'vertex_group_delete')
	
	def execute(self, context):
		source_objs = []
		for obj in context.selected_objects:
			if (obj.type == 'MESH' and context.active_object.name != obj.name):
				source_objs.append(obj)
		if (0 < len(context.active_object.vertex_groups) and self.vertex_group_remove_all):
			bpy.ops.object.vertex_group_remove(all=True)
		me = context.active_object.data
		vert_mapping = 'NEAREST'
		for obj in source_objs:
			if (len(obj.data.polygons) <= 0):
				for obj2 in source_objs:
					if (len(obj.data.edges) <= 0):
						break
				else:
					vert_mapping = 'EDGEINTERP_NEAREST'
				break
		else:
			vert_mapping = 'POLYINTERP_NEAREST'
		bpy.ops.object.data_transfer(use_reverse_transfer=True, data_type='VGROUP_WEIGHTS', use_create=True, vert_mapping=vert_mapping, layers_select_src = 'ALL', layers_select_dst = 'NAME')
		if (self.vertex_group_clean):
			bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0, keep_single=False)
		if (self.vertex_group_delete):
			obj = context.active_object
			for vg in obj.vertex_groups:
				for vert in obj.data.vertices:
					try:
						if (vg.weight(vert.index) > 0.0):
							break
					except RuntimeError:
						pass
				else:
					obj.vertex_groups.remove(vg)
		return {'FINISHED'}

# シェイプキー強制転送
class shape_key_transfer_ex(bpy.types.Operator):
	bl_idname = 'object.shape_key_transfer_ex'
	bl_label = "シェイプキー強制転送"
	bl_description = "頂点数の違うメッシュ同士でも一番近い頂点からシェイプキーを強制転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if len(context.selected_objects) != 2:
			return False
		for ob in context.selected_objects:
			if ob.type != 'MESH':
				return False
			if ob.name != context.active_object.name:
				if not ob.data.shape_keys:
					return False
		return True
	
	def execute(self, context):
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
		bm = bmesh.new()
		bm.from_mesh(source_ob.data)
		bm.faces.ensure_lookup_table()
		kd = mathutils.kdtree.KDTree(len(bm.faces))
		for i, face in enumerate(bm.faces):
			kd.insert(face.calc_center_median(), i)
		kd.balance()
		for key_block in source_ob.data.shape_keys.key_blocks:
			if not target_ob.data.shape_keys:
				target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
			else:
				if key_block.name not in target_ob.data.shape_keys.key_blocks.keys():
					target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
				else:
					target_shape = target_ob.data.shape_keys.key_blocks[key_block.name]
			for target_vert in target_ob.data.vertices:
				co, index, dist = kd.find(target_vert.co)
				face = bm.faces[index]
				total_len = 0
				for vert in face.verts:
					vec = target_vert.co - vert.co
					total_len += vec.length
				total_diff = mathutils.Vector((0, 0, 0))
				total_multi = 0
				for vert in face.verts:
					diff = key_block.data[vert.index].co - source_ob.data.vertices[vert.index].co
					multi = total_len - vec.length
					total_diff += diff * multi
					total_multi += multi
				total_diff /= total_multi
				target_shape.data[target_vert.index].co = target_ob.data.vertices[target_vert.index].co + total_diff
		return {'FINISHED'}

# 頂点グループメニューに項目追加
def MESH_MT_vertex_group_specials(self, context):
	self.layout.separator()
	self.layout.operator(vertex_group_transfer.bl_idname, icon='SPACE2')

# シェイプメニューに項目追加
def MESH_MT_shape_key_specials(self, context):
	self.layout.separator()
	self.layout.operator(shape_key_transfer_ex.bl_idname, icon='SPACE2')
