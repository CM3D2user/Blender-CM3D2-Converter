import bpy

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
		for key_block in source_ob.data.shape_keys.key_blocks:
			if not target_ob.data.shape_keys:
				target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
			else:
				if key_block.name not in target_ob.data.shape_keys.key_blocks.keys():
					target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
			for target_vert in target_ob.data.vertices:
				min_len = 999999999
				min_index = None
				for source_vert in source_ob.data.vertices:
					vec = target_vert.co - source_vert.co
					if vec.length < min_len:
						min_len = vec.length
						min_index = source_vert.index
				vec = key_block.data[min_index].co - source_ob.data.vertices[min_index].co
				target_shape.data[target_vert.index].co = target_ob.data.vertices[target_vert.index].co + vec
		return {'FINISHED'}

# シェイプメニューに項目追加
def MESH_MT_shape_key_specials(self, context):
	self.layout.separator()
	self.layout.operator(shape_key_transfer_ex.bl_idname, icon='SPACE2')
