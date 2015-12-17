import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	col = self.layout.column(align=True)
	col.label(text="CM3D2", icon_value=common.preview_collections['main']['KISS'].icon_id)
	row = col.row(align=True)
	row.operator('object.quick_ao_bake_image', icon='BRUSH_TEXFILL')
	row.operator('object.quick_dirty_bake_image', icon='MATSPHERE')
	row = col.row(align=True)
	row.operator('object.quick_hemi_bake_image', icon='LAMP_HEMI')
	row.operator('object.quick_hair_bake_image', icon='PARTICLEMODE')

class quick_ao_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_ao_bake_image'
	bl_label = "AO・ベイク"
	bl_description = "アクティブオブジェクトに素早くAOをベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	image_width = bpy.props.IntProperty(name="幅", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	image_height = bpy.props.IntProperty(name="高さ", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	
	items = [
		('RAYTRACE', "レイトレース", "", 'BRUSH_TEXFILL', 1),
		('APPROXIMATE', "近似(AAO)", "", 'MATSPHERE', 2),
		]
	ao_gather_method = bpy.props.EnumProperty(items=items, name="処理方法", default='RAYTRACE')
	ao_samples = bpy.props.IntProperty(name="精度", default=10, min=1, max=50, soft_min=1, soft_max=50)
	ao_hide_other = bpy.props.BoolProperty(name="他オブジェクトの影響を受けない", default=True)
	
	@classmethod
	def poll(cls, context):
		if len(context.selected_objects) != 1:
			return False
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if len(me.uv_layers):
					return True
		return False
	
	def invoke(self, context, event):
		ob = context.active_object
		self.image_name = ob.name + " AO Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="AO設定", icon='BRUSH_TEXFILL')
		self.layout.prop(self, 'ao_gather_method', icon='NODETREE')
		self.layout.prop(self, 'ao_samples', icon='ANIM_DATA')
		self.layout.prop(self, 'ao_hide_other', icon='VISIBLE_IPO_OFF')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		img = context.blend_data.images.new(self.image_name, self.image_width, self.image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			for space in area.spaces:
				if space.type == 'IMAGE_EDITOR':
					space.image = img
					break
		
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		context.scene.world.light_settings.gather_method = self.ao_gather_method
		context.scene.world.light_settings.samples = self.ao_samples
		context.scene.render.bake_type = 'AO'
		context.scene.render.use_bake_normalize = True
		
		if self.ao_hide_other: hide_render_restore = common.hide_render_restore()
		
		bpy.ops.object.bake_image()
		
		if self.ao_hide_other: hide_render_restore.restore()
		
		return {'FINISHED'}

class quick_dirty_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_dirty_bake_image'
	bl_label = "擬似AO・ベイク"
	bl_description = "アクティブオブジェクトに素早く擬似AOをベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	image_width = bpy.props.IntProperty(name="幅", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	image_height = bpy.props.IntProperty(name="高さ", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	
	blur_strength = bpy.props.FloatProperty(name="ブラー強度", default=1, min=0.01, max=1, soft_min=0.01, soft_max=1, step=10, precision=2)
	dirt_count = bpy.props.IntProperty(name="処理回数", default=1, min=1, max=3, soft_min=1, soft_max=3)
	
	@classmethod
	def poll(cls, context):
		if len(context.selected_objects) != 1:
			return False
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if len(me.uv_layers):
					return True
		return False
	
	def invoke(self, context, event):
		ob = context.active_object
		self.image_name = ob.name + " Dirty Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="擬似AO設定", icon='BRUSH_TEXFILL')
		row = self.layout.row(align=True)
		row.prop(self, 'blur_strength', icon='BRUSH_BLUR', slider=True)
		row.prop(self, 'dirt_count', icon='FILE_REFRESH')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		img = context.blend_data.images.new(self.image_name, self.image_width, self.image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			for space in area.spaces:
				if space.type == 'IMAGE_EDITOR':
					space.image = img
					break
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		pre_vertex_color_active_index = me.vertex_colors.active_index
		vertex_color = me.vertex_colors.new(name="quick_dirty_bake_image_temp")
		me.vertex_colors.active = vertex_color
		
		for i in range(self.dirt_count):
			bpy.ops.paint.vertex_color_dirt(override, blur_strength=self.blur_strength, blur_iterations=1, clean_angle=3.14159, dirt_angle=0, dirt_only=True)
		
		material_restore = common.material_restore(ob)
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = context.blend_data.materials.new("quick_dirty_bake_image_temp")
		ob.material_slots[0].material = temp_mate
		temp_mate.use_vertex_color_paint = True
		
		context.scene.render.bake_type = 'TEXTURE'
		context.scene.render.use_bake_selected_to_active = False
		
		bpy.ops.object.bake_image()
		
		common.remove_data(temp_mate)
		
		material_restore.restore()
		
		me.vertex_colors.remove(vertex_color)
		me.vertex_colors.active_index = pre_vertex_color_active_index
		
		return {'FINISHED'}

class quick_hemi_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_hemi_bake_image'
	bl_label = "ヘミライト・ベイク"
	bl_description = "アクティブオブジェクトに素早くヘミライトの陰をベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	image_width = bpy.props.IntProperty(name="幅", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	image_height = bpy.props.IntProperty(name="高さ", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	
	lamp_energy = bpy.props.FloatProperty(name="光の強さ", default=1, min=0, max=2, soft_min=0, soft_max=2, step=50, precision=2)
	
	use_ao = bpy.props.BoolProperty(name="AOを使用", default=False)
	ao_samples = bpy.props.IntProperty(name="AOの精度", default=10, min=1, max=50, soft_min=1, soft_max=50)
	ao_hide_other = bpy.props.BoolProperty(name="他オブジェクトの影響を受けない", default=True)
	
	@classmethod
	def poll(cls, context):
		if len(context.selected_objects) != 1:
			return False
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if len(me.uv_layers):
					return True
		return False
	
	def invoke(self, context, event):
		ob = context.active_object
		self.image_name = ob.name + " Hemi Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="ヘミライト設定", icon='LAMP_HEMI')
		self.layout.prop(self, 'lamp_energy', icon='LAMP_POINT', slider=True)
		self.layout.label(text="AO設定", icon='BRUSH_TEXFILL')
		row = self.layout.row(align=True)
		row.prop(self, 'use_ao', icon='FILE_TICK')
		row.prop(self, 'ao_samples', icon='ANIM_DATA')
		self.layout.prop(self, 'ao_hide_other', icon='VISIBLE_IPO_OFF')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		img = context.blend_data.images.new(self.image_name, self.image_width, self.image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			for space in area.spaces:
				if space.type == 'IMAGE_EDITOR':
					space.image = img
					break
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		if self.ao_hide_other: hide_render_restore = common.hide_render_restore()
		material_restore = common.material_restore(ob)
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = context.blend_data.materials.new("quick_hemi_bake_image_temp")
		ob.material_slots[0].material = temp_mate
		temp_mate.diffuse_intensity = 1.0
		temp_mate.diffuse_color = (1, 1, 1)
		
		temp_lamp = context.blend_data.lamps.new("quick_hemi_bake_image_temp", 'HEMI')
		temp_ob = context.blend_data.objects.new("quick_hemi_bake_image_temp", temp_lamp)
		context.scene.objects.link(temp_ob)
		temp_lamp.energy = self.lamp_energy
		
		context.scene.world.light_settings.use_ambient_occlusion = self.use_ao
		if self.use_ao:
			context.scene.world.light_settings.samples = self.ao_samples
			context.scene.world.light_settings.ao_blend_type = 'MULTIPLY'
		
		context.scene.render.bake_type = 'FULL'
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_lamp, temp_ob, temp_mate])
		
		material_restore.restore()
		if self.ao_hide_other: hide_render_restore.restore()
		
		return {'FINISHED'}

class quick_hair_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_hair_bake_image'
	bl_label = "ヘアー・ベイク"
	bl_description = "アクティブオブジェクトに素早くCM3D2の髪風のテクスチャをベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	image_width = bpy.props.IntProperty(name="幅", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	image_height = bpy.props.IntProperty(name="高さ", default=1024, min=1, max=8192, soft_min=1, soft_max=8192, subtype='PIXEL')
	
	mate_diffuse_color = bpy.props.FloatVectorProperty(name="髪色", default=(1, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=3)
	mate_angel_ring_factor = bpy.props.FloatProperty(name="天使の輪の強さ", default=0.5, min=0, max=1, soft_min=0, soft_max=1, step=50, precision=2)
	
	lamp_energy = bpy.props.FloatProperty(name="光の強さ", default=1, min=0, max=2, soft_min=0, soft_max=2, step=50, precision=2)
	
	use_ao = bpy.props.BoolProperty(name="AOを使用", default=False)
	ao_samples = bpy.props.IntProperty(name="AOの精度", default=10, min=1, max=50, soft_min=1, soft_max=50)
	ao_hide_other = bpy.props.BoolProperty(name="他オブジェクトの影響を受けない", default=True)
	
	@classmethod
	def poll(cls, context):
		if len(context.selected_objects) != 1:
			return False
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if len(me.uv_layers):
					return True
		return False
	
	def invoke(self, context, event):
		ob = context.active_object
		self.image_name = ob.name + " Hair Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="ヘアー設定", icon='PARTICLEMODE')
		self.layout.prop(self, 'mate_diffuse_color', icon='COLOR')
		self.layout.prop(self, 'mate_angel_ring_factor', icon='MATCAP_09', slider=True)
		self.layout.label(text="ヘミライト設定", icon='LAMP_HEMI')
		self.layout.prop(self, 'lamp_energy', icon='LAMP_POINT', slider=True)
		self.layout.label(text="AO設定", icon='BRUSH_TEXFILL')
		row = self.layout.row(align=True)
		row.prop(self, 'use_ao', icon='FILE_TICK')
		row.prop(self, 'ao_samples', icon='ANIM_DATA')
		self.layout.prop(self, 'ao_hide_other', icon='VISIBLE_IPO_OFF')
	
	def execute(self, context):
		import os.path
		
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		img = context.blend_data.images.new(self.image_name, self.image_width, self.image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			for space in area.spaces:
				if space.type == 'IMAGE_EDITOR':
					space.image = img
					break
		
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		if self.ao_hide_other: hide_render_restore = common.hide_render_restore()
		material_restore = common.material_restore(ob)
		
		temp_lamp = context.blend_data.lamps.new("quick_hemi_bake_image_lamp_temp", 'HEMI')
		temp_lamp_ob = context.blend_data.objects.new("quick_hemi_bake_image_lamp_temp", temp_lamp)
		context.scene.objects.link(temp_lamp_ob)
		temp_lamp.energy = self.lamp_energy
		
		pre_scene_camera = context.scene.camera
		temp_camera = context.blend_data.cameras.new("quick_hemi_bake_image_camera_temp")
		temp_camera_ob = context.blend_data.objects.new("quick_hemi_bake_image_camera_temp", temp_camera)
		context.scene.objects.link(temp_camera_ob)
		temp_camera_ob.rotation_euler[0] = 1.5708
		context.scene.camera = temp_camera_ob
		
		context.scene.world.light_settings.use_ambient_occlusion = self.use_ao
		if self.use_ao:
			context.scene.world.light_settings.samples = self.ao_samples
			context.scene.world.light_settings.ao_blend_type = 'MULTIPLY'
		context.scene.render.bake_type = 'FULL'
		
		blend_path = os.path.join(os.path.dirname(__file__), "append_data.blend")
		with context.blend_data.libraries.load(blend_path) as (data_from, data_to):
			data_to.materials = ["CM3D2 Hair"]
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = data_to.materials[0]
		ob.material_slots[0].material = temp_mate
		
		temp_mate.diffuse_color = self.mate_diffuse_color
		temp_mate.node_tree.nodes["mate_angel_ring_factor"].inputs[0].default_value = self.mate_angel_ring_factor
		
		bpy.ops.object.bake_image()
		
		temp_tex = temp_mate.texture_slots[0].texture
		
		common.remove_data([temp_mate, temp_tex, temp_camera_ob, temp_camera, temp_lamp_ob, temp_lamp])
		context.scene.camera = pre_scene_camera
		
		material_restore.restore()
		if self.ao_hide_other: hide_render_restore.restore()
		
		return {'FINISHED'}
