import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	self.layout.separator()
	self.layout.operator('pose.apply_prime_field', icon_value=common.preview_collections['main']['KISS'].icon_id)

class apply_prime_field(bpy.types.Operator):
	bl_idname = 'pose.apply_prime_field'
	bl_label = "現在のポーズで素体化"
	bl_description = "現在のポーズで衣装をモデリングしやすくする素体を作成します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_apply_armature_modifier = bpy.props.BoolProperty(name="関係するメッシュのアーマチュアを適用", default=True)
	is_deform_preserve_volume = bpy.props.BoolProperty(name="アーマチュア適用は体積を維持", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_apply_armature_modifier')
		self.layout.prop(self, 'is_deform_preserve_volume')
	
	def execute(self, context):
		ob = context.active_object
		arm = ob.data
		pose = ob.pose
		
		pre_selected_objects = context.selected_objects
		pre_selected_pose_bones = context.selected_pose_bones
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.ops.object.select_all(action='DESELECT')
		ob.select = True
		
		if self.is_apply_armature_modifier:
			for o in context.blend_data.objects:
				if o.type == 'MESH' and len(o.modifiers):
					is_applies = [False] * 32
					for i, mod in enumerate(o.modifiers):
						if mod.type == 'ARMATURE':
							if mod.object and mod.object.name == ob.name:
								is_applies[i] = True
								if self.is_deform_preserve_volume:
									mod.use_deform_preserve_volume = True
					if any(is_applies):
						override = context.copy()
						override['object'], override['active_object'] = o, o
						bpy.ops.object.forced_modifier_apply(override, is_applies=is_applies)
		
		temp_ob = ob.copy()
		temp_arm = arm.copy()
		temp_ob.data = temp_arm
		context.scene.objects.link(temp_ob)
		
		context.scene.objects.active = temp_ob
		bpy.ops.object.mode_set(mode='POSE')
		bpy.ops.pose.select_all(action='SELECT')
		bpy.ops.pose.transforms_clear()
		
		context.scene.objects.active = ob
		bpy.ops.object.mode_set(mode='POSE')
		bpy.ops.pose.select_all(action='SELECT')
		bpy.ops.pose.armature_apply()
		bpy.ops.pose.constraints_clear()
		
		consts = []
		for bone in pose.bones:
			const = bone.constraints.new('COPY_TRANSFORMS')
			const.target = temp_ob
			const.subtarget = bone.name
			consts.append(const)
		
		for i in range(10):
			for const in consts:
				const.mute = bool(i % 2)
			
			if i % 2:
				bpy.ops.pose.visual_transform_apply()
			else:
				bpy.ops.pose.transforms_clear()
			
			for bone in pose.bones:
				bone.keyframe_insert(data_path='location', frame=i)
				bone.keyframe_insert(data_path='rotation_quaternion', frame=i)
				bone.keyframe_insert(data_path='rotation_euler', frame=i)
				bone.keyframe_insert(data_path='scale', frame=i)
		bpy.ops.pose.constraints_clear()
		
		common.remove_data(temp_arm)
		common.remove_data(temp_ob)
		
		bpy.ops.pose.select_all(action='DESELECT')
		for bone in pre_selected_pose_bones:
			arm.bones[bone.name].select = True
		
		arm['is T Stance'] = 1
		
		for o in pre_selected_objects:
			o.select = True
		context.scene.objects.active = ob
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}
