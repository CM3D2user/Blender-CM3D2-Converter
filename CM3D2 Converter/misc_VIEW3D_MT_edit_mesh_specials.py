import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	icon_id = common.preview_collections['main']['KISS'].icon_id
	self.layout.separator()
	self.layout.operator('mesh.selected_face_sort_front', text="選択面の描画順を最前面に", icon_value=icon_id).is_back = False
	self.layout.operator('mesh.selected_face_sort_front', text="選択面の描画順を最背面に", icon_value=icon_id).is_back = True

class selected_mesh_sort_front(bpy.types.Operator):
	bl_idname = 'mesh.selected_face_sort_front'
	bl_label = "選択面の描画順を最前面に"
	bl_description = "選択中の面の描画順を最も前面/背面に並び替えます"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_back = bpy.props.BoolProperty(name="最背面")
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob.type != 'MESH': return False
		return True
	
	def execute(self, context):
		ob = context.active_object
		if ob.mode != 'EDIT':
			self.report(type={'ERROR'}, message="エディットモードで実行してください")
			return {'CANCELLED'}
		me = ob.data
		bm = bmesh.from_edit_mesh(me)
		
		bm.faces.ensure_lookup_table()
		
		selected_face_indexs = []
		other_face_indexs = []
		for face in bm.faces:
			if face.select:
				selected_face_indexs.append(face.index)
			else:
				other_face_indexs.append(face.index)
		
		output_face_indexs = []
		if not self.is_back:
			output_face_indexs = other_face_indexs + selected_face_indexs
		else:
			output_face_indexs = selected_face_indexs + other_face_indexs
		
		for for_index, sorted_index in enumerate(output_face_indexs):
			bm.faces[sorted_index].index = for_index
		
		bm.faces.sort()
		bmesh.update_edit_mesh(me)
		return {'FINISHED'}
