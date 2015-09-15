import bpy, bmesh, mathutils

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
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label("計算に非常に時間が掛かる場合があります")
		self.layout.label("可能であれば参考メッシュを削ってから実行を")
	
	def execute(self, context):
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
		bm = bmesh.new()
		bm.from_mesh(source_ob.data)
		bm.faces.ensure_lookup_table()
		for key_block in source_ob.data.shape_keys.key_blocks:
			if not target_ob.data.shape_keys:
				target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
			else:
				if key_block.name not in target_ob.data.shape_keys.key_blocks.keys():
					target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
				else:
					target_shape = target_ob.data.shape_keys.key_blocks[key_block.name]
			for target_vert in target_ob.data.vertices:
				min_len = 999999999
				min_index = None
				for face in bm.faces:
					vec = target_vert.co - face.calc_center_median()
					if vec.length < min_len:
						min_len = vec.length
						min_index = face.index
				face = bm.faces[min_index]
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

# シェイプメニューに項目追加
def MESH_MT_shape_key_specials(self, context):
	self.layout.separator()
	self.layout.operator(shape_key_transfer_ex.bl_idname, icon='SPACE2')
