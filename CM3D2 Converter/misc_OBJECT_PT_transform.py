# 「プロパティ」エリア → 「オブジェクト」タブ → 「トランスフォーム」パネル
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	self.layout.operator('object.sync_object_transform', icon_value=common.preview_collections['main']['KISS'].icon_id)

class sync_object_transform(bpy.types.Operator):
	bl_idname = 'object.sync_object_transform'
	bl_label = "オブジェクトの位置を合わせる"
	bl_description = "アクティブオブジェクトの中心位置を、他の選択オブジェクトの中心位置に合わせます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		obs = context.selected_objects
		return len(obs) == 2
	
	def execute(self, context):
		target_ob = context.active_object
		for ob in context.selected_objects:
			if target_ob.name != ob.name:
				source_ob = ob
				break
		
		for area in context.screen.areas:
			if area.type == 'VIEW_3D':
				for space in area.spaces:
					if space.type == 'VIEW_3D':
						target_space = space
						break
		
		pre_cursor_location = target_space.cursor_location[:]
		target_space.cursor_location = source_ob.location[:]
		
		source_ob.select = False
		bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
		source_ob.select = True
		
		target_space.cursor_location = pre_cursor_location[:]
		return {'FINISHED'}
