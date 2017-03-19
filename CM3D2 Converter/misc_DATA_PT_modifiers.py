import os, re, sys, bpy, time, bmesh, mathutils, math
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	ob = context.active_object
	if ob:
		if ob.type == 'MESH':
			me = ob.data
			if len(ob.modifiers):
				self.layout.operator('object.forced_modifier_apply', icon_value=common.preview_collections['main']['KISS'].icon_id)

class forced_modifier_apply(bpy.types.Operator):
	bl_idname = 'object.forced_modifier_apply'
	bl_label = "モディファイア強制適用"
	bl_description = "シェイプキーのあるメッシュのモディファイアでも強制的に適用します"
	bl_options = {'REGISTER', 'UNDO'}
	
	custom_normal_blend = bpy.props.FloatProperty(name="CM3D2用法線のブレンド率", default=0.5, min=0, max=1, soft_min=0, soft_max=1, step=3, precision=0)
	is_applies = bpy.props.BoolVectorProperty(name="適用するモディファイア", size=32, options={'SKIP_SAVE'})
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		return len(ob.modifiers)
	
	def invoke(self, context, event):
		ob = context.active_object
		if len(ob.modifiers) == 0:
			return {'CANCELLED'}
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'custom_normal_blend', icon='SNAP_NORMAL', slider=True)
		self.layout.label("適用するモディファイア")
		ob = context.active_object
		for index, mod in enumerate(ob.modifiers):
			icon = 'MOD_%s' % mod.type
			try:
				self.layout.prop(self, 'is_applies', text=mod.name, index=index, icon=icon)
			except:
				self.layout.prop(self, 'is_applies', text=mod.name, index=index, icon='MODIFIER')
			
			if mod.show_viewport:
				self.is_applies[index] = True
	
	def execute(self, context):
		bpy.ops.object.mode_set(mode='OBJECT')
		ob = context.active_object
		me = ob.data
		
		arm_ob = None
		for mod in ob.modifiers:
			if mod.type == "ARMATURE":
				arm_ob = mod.object
		
		if arm_ob:
			ob.active_shape_key_index = 0
			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.object.mode_set(mode='OBJECT')
			
			arm = arm_ob.data
			arm_pose = arm_ob.pose
			
			pose_quats = {}
			for bone in arm.bones:
				pose_bone = arm_pose.bones[bone.name]
				
				bone_quat = bone.matrix_local.to_quaternion()
				pose_quat = pose_bone.matrix.to_quaternion()
				result_quat = pose_quat * bone_quat.inverted()
				
				pose_quats[bone.name] = result_quat.copy()
			
			custom_normals = []
			for loop in me.loops:
				vert = me.vertices[loop.vertex_index]
				no = vert.normal.copy()
				
				total_weight = 0.0
				for vge in vert.groups:
					total_weight += vge.weight
				
				total_quat = mathutils.Quaternion()
				for vge in vert.groups:
					vg = ob.vertex_groups[vge.group]
					total_quat = total_quat.slerp(pose_quats[vg.name], vge.weight / total_weight)
				
				no.rotate(total_quat)
				custom_normals.append(no)
		
		pre_selected_objects = context.selected_objects[:]
		pre_mode = ob.mode
		
		if me.shape_keys:
			pre_relative_keys = [s.relative_key.name for s in me.shape_keys.key_blocks]
			pre_active_shape_key_index = ob.active_shape_key_index
			
			shape_names = [s.name for s in me.shape_keys.key_blocks]
			shape_deforms = []
			for shape in me.shape_keys.key_blocks:
				shape_deforms.append([shape.data[v.index].co.copy() for v in me.vertices])
			
			ob.active_shape_key_index = len(me.shape_keys.key_blocks) - 1
			for i in me.shape_keys.key_blocks[:]:
				ob.shape_key_remove(ob.active_shape_key)
			
			new_shape_deforms = []
			for shape_index, deforms in enumerate(shape_deforms):
				
				temp_ob = ob.copy()
				temp_me = me.copy()
				temp_ob.data = temp_me
				context.scene.objects.link(temp_ob)
				
				for vert in temp_me.vertices:
					vert.co = deforms[vert.index].copy()
				
				override = context.copy()
				override['object'] = temp_ob
				for index, mod in enumerate(temp_ob.modifiers):
					if self.is_applies[index]:
						try:
							bpy.ops.object.modifier_apply(override, modifier=mod.name)
						except: pass
				
				new_shape_deforms.append([v.co.copy() for v in temp_me.vertices])
				
				common.remove_data(temp_ob)
				common.remove_data(temp_me)
		
		for index, mod in enumerate(ob.modifiers[:]):
			if self.is_applies[index]:
				try:
					bpy.ops.object.modifier_apply(modifier=mod.name)
				except:
					ob.modifiers.remove(mod)
		
		context.scene.objects.active = ob
		
		if me.shape_keys:
			for shape_index, deforms in enumerate(new_shape_deforms):
				
				bpy.ops.object.shape_key_add(from_mix=False)
				shape = ob.active_shape_key
				shape.name = shape_names[shape_index]
				
				for vert in me.vertices:
					shape.data[vert.index].co = deforms[vert.index].copy()
			
			for shape_index, shape in enumerate(me.shape_keys.key_blocks):
				shape.relative_key = me.shape_keys.key_blocks[pre_relative_keys[shape_index]]
			
			ob.active_shape_key_index = pre_active_shape_key_index
		
		for temp_ob in pre_selected_objects:
			temp_ob.select = True
		bpy.ops.object.mode_set(mode=pre_mode)
		
		if arm_ob:
			for i, loop in enumerate(me.loops):
				vert = me.vertices[loop.vertex_index]
				no = vert.normal.copy()
				
				custom_rot = mathutils.Vector((0.0, 0.0, 1.0)).rotation_difference(custom_normals[i])
				original_rot = mathutils.Vector((0.0, 0.0, 1.0)).rotation_difference(no)
				output_rot = original_rot.slerp(custom_rot, self.custom_normal_blend)
				
				output_no = mathutils.Vector((0.0, 0.0, 1.0))
				output_no.rotate(output_rot)
				
				custom_normals[i] = output_no
			me.use_auto_smooth = True
			me.normals_split_custom_set(custom_normals)
		
		return {'FINISHED'}
