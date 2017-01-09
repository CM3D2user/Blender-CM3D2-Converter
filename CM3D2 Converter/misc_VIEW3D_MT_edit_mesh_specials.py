import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	icon_id = common.preview_collections['main']['KISS'].icon_id
	self.layout.separator()
	self.layout.operator('mesh.selected_mesh_sort_front', text="選択メッシュの描画順を最前面に", icon_value=icon_id).is_back = False
	self.layout.operator('mesh.selected_mesh_sort_front', text="選択メッシュの描画順を最背面に", icon_value=icon_id).is_back = True

class selected_mesh_sort_front(bpy.types.Operator):
	bl_idname = 'mesh.selected_mesh_sort_front'
	bl_label = "選択メッシュの描画順を最前面に"
	bl_description = "選択中のメッシュの描画順を最も前面にソートします"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_back = bpy.props.BoolProperty(name="最背面")
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob.type != 'MESH': return False
		return True
	
	def execute(self, context):
		pre_obs = []
		for ob in context.selectable_objects:
			pre_obs.append(ob.name)
		
		source_ob = context.active_object
		pre_ob_name = source_ob.name
		pre_me_name = source_ob.data.name
		
		bpy.ops.mesh.separate(type='SELECTED')
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.ops.object.select_all(action='DESELECT')
		
		source_ob.select = True
		for ob in context.selectable_objects:
			if (not ob.name in pre_obs):
				ob.select = True
				new_ob = ob
				break
		for vert in new_ob.data.vertices:
			vert.select = True
		
		if not self.is_back:
			context.scene.objects.active = source_ob
		else:
			context.scene.objects.active = new_ob
		
		bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
		bpy.ops.object.join()
		
		context.scene.objects.active.name = pre_ob_name
		context.scene.objects.active.data.name = pre_me_name
		
		bpy.ops.object.mode_set(mode='EDIT')
		return {'FINISHED'}
