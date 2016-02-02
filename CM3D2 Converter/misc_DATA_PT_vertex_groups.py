import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	import re
	ob = context.active_object
	if not ob: return
	if not len(ob.vertex_groups) and ob.type != 'MESH': return
	
	flag = False
	for vertex_group in ob.vertex_groups:
		if not flag and re.search(r'[_ ]([rRlL])[_ ]', vertex_group.name):
			flag = True
		if not flag and vertex_group.name.count('*') == 1:
			if re.search(r'\.([rRlL])$', vertex_group.name):
				flag = True
		if flag:
			col = self.layout.column(align=True)
			col.label(text="CM3D2用 頂点グループ名変換", icon_value=common.preview_collections['main']['KISS'].icon_id)
			row = col.row(align=True)
			row.operator('object.decode_cm3d2_vertex_group_names', icon='BLENDER', text="CM3D2 → Blender")
			row.operator('object.encode_cm3d2_vertex_group_names', icon_value=common.preview_collections['main']['KISS'].icon_id, text="Blender → CM3D2")
			break

class decode_cm3d2_vertex_group_names(bpy.types.Operator):
	bl_idname = 'object.decode_cm3d2_vertex_group_names'
	bl_label = "頂点グループ名をCM3D2用→Blender用に変換"
	bl_description = "CM3D2で使われてるボーン名(頂点グループ名)をBlenderで左右対称編集できるように変換します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		import re
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				if ob.vertex_groups.active:
					for vg in ob.vertex_groups:
						if re.search(r'[_ ]([rRlL])[_ ]', vg.name):
							return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		convert_count = 0
		context.window_manager.progress_begin(0, len(ob.vertex_groups))
		for vg_index, vg in enumerate(ob.vertex_groups[:]):
			context.window_manager.progress_update(vg_index)
			vg_name = common.decode_bone_name(vg.name)
			if vg_name != vg.name:
				if vg_name in ob.vertex_groups:
					target_vg = ob.vertex_groups[vg_name]
					for vert in me.vertices:
						try:
							weight = vg.weight(vert.index)
						except:
							weight = 0.0
						try:
							target_weight = target_vg.weight(vert.index)
						except:
							target_weight = 0.0
						if 0.0 < weight + target_weight:
							target_vg.add([vert.index], weight + target_weight, 'REPLACE')
					ob.vertex_groups.remove(vg)
				else:
					vg.name = vg_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="頂点グループ名をBlender用に変換しました")
		context.window_manager.progress_end()
		return {'FINISHED'}

class encode_cm3d2_vertex_group_names(bpy.types.Operator):
	bl_idname = 'object.encode_cm3d2_vertex_group_names'
	bl_label = "頂点グループ名をBlender用→CM3D2用に変換"
	bl_description = "CM3D2で使われてるボーン名(頂点グループ名)に戻します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		import re
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				if ob.vertex_groups.active:
					for vg in ob.vertex_groups:
						if vg.name.count('*') == 1 and re.search(r'\.([rRlL])$', vg.name):
							return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		convert_count = 0
		context.window_manager.progress_begin(0, len(ob.vertex_groups))
		for vg_index, vg in enumerate(ob.vertex_groups[:]):
			context.window_manager.progress_update(vg_index)
			vg_name = common.encode_bone_name(vg.name)
			if vg_name != vg.name:
				if vg_name in ob.vertex_groups:
					target_vg = ob.vertex_groups[vg_name]
					for vert in me.vertices:
						try:
							weight = vg.weight(vert.index)
						except:
							weight = 0.0
						try:
							target_weight = target_vg.weight(vert.index)
						except:
							target_weight = 0.0
						if 0.0 < weight + target_weight:
							target_vg.add([vert.index], weight + target_weight, 'REPLACE')
					ob.vertex_groups.remove(vg)
				else:
					vg.name = vg_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="頂点グループ名をCM3D2用に戻しました")
		context.window_manager.progress_end()
		return {'FINISHED'}
