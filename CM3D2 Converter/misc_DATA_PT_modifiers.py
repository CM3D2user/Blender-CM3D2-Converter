import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	ob = context.active_object
	if ob:
		if ob.type == 'MESH':
			me = ob.data
			if me.shape_keys and len(ob.modifiers):
				self.layout.operator('object.forced_modifier_apply', icon_value=common.preview_collections['main']['KISS'].icon_id)

class forced_modifier_apply(bpy.types.Operator):
	bl_idname = 'object.forced_modifier_apply'
	bl_label = "モディファイア強制適用"
	bl_description = "シェイプキーのあるメッシュのモディファイアでも強制的に適用します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_applies = bpy.props.BoolVectorProperty(name="適用するモディファイア", size=32, options={'SKIP_SAVE'})
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH' and len(ob.modifiers):
				me = ob.data
				if me.shape_keys:
					return True
		return False
	
	def invoke(self, context, event):
		ob = context.active_object
		if len(ob.modifiers) == 0:
			return {'CANCELLED'}
		elif len(ob.modifiers) == 1:
			self.is_applies[0] = True
			return self.execute(context)
		else:
			return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
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
		
		pre_relative_keys = [s.relative_key.name for s in me.shape_keys.key_blocks]
		pre_active_shape_key_index = ob.active_shape_key_index
		pre_selected_objects = context.selected_objects[:]
		pre_mode = ob.mode
		
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
			
			common.remove_data(temp_me)
			common.remove_data(temp_ob)
		
		for index, mod in enumerate(ob.modifiers[:]):
			if self.is_applies[index]:
				try:
					bpy.ops.object.modifier_apply(modifier=mod.name)
				except:
					ob.modifiers.remove(mod)
		
		context.scene.objects.active = ob
		for shape_index, deforms in enumerate(new_shape_deforms):
			
			bpy.ops.object.shape_key_add(from_mix=False)
			shape = ob.active_shape_key
			shape.name = shape_names[shape_index]
			
			for vert in me.vertices:
				shape.data[vert.index].co = deforms[vert.index].copy()
		
		for shape_index, shape in enumerate(me.shape_keys.key_blocks):
			shape.relative_key = me.shape_keys.key_blocks[pre_relative_keys[shape_index]]
		
		ob.active_shape_key_index = pre_active_shape_key_index
		for o in pre_selected_objects:
			o.select = True
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}
