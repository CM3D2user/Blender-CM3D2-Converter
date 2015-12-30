import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	col = self.layout.column(align=True)
	col.label(text="CM3D2用ベイク", icon_value=common.preview_collections['main']['KISS'].icon_id)
	row = col.row(align=True)
	row.operator('object.add_bake_image', icon='IMAGE_COL', text="新規画像")
	row.operator('object.quick_ao_bake_image', icon='BRUSH_TEXFILL', text="AO")
	row.operator('object.quick_dirty_bake_image', icon='MATSPHERE', text="擬似AO")
	row = col.row(align=True)
	row.operator('object.quick_hemi_bake_image', icon='LAMP_HEMI', text="ヘミライト")
	row.operator('object.quick_shadow_bake_image', icon='IMAGE_ALPHA', text="影")
	row.operator('object.quick_side_shadow_bake_image', icon='ARROW_LEFTRIGHT', text="側面陰")
	row = col.row(align=True)
	row.operator('object.quick_gradation_bake_image', icon='MESH_PLANE', text="グラデーション")
	row.operator('object.quick_metal_bake_image', icon='MATCAP_19', text="金属")
	row.operator('object.quick_hair_bake_image', icon='PARTICLEMODE', text="髪")

class add_bake_image(bpy.types.Operator):
	bl_idname = 'object.add_bake_image'
	bl_label = "ベイク用の画像を作成"
	bl_description = "アクティブオブジェクトに素早くベイク用の空の画像を用意します"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	image_color = bpy.props.FloatVectorProperty(name="色", default=(1, 1, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=4)
	
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
		self.image_name = ob.name + " Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.prop(self, 'image_color', icon='COLOR')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		
		img.generated_color = self.image_color
		
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		return {'FINISHED'}

class quick_ao_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_ao_bake_image'
	bl_label = "AO・ベイク"
	bl_description = "アクティブオブジェクトに素早くAOをベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
	items = [
		('RAYTRACE', "レイトレース", "", 'BRUSH_TEXFILL', 1),
		('APPROXIMATE', "近似(AAO)", "", 'MATSPHERE', 2),
		]
	ao_gather_method = bpy.props.EnumProperty(items=items, name="処理方法", default='RAYTRACE')
	ao_samples = bpy.props.IntProperty(name="精度", default=20, min=1, max=50, soft_min=1, soft_max=50)
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
		self.layout.prop(self, 'ao_gather_method', icon='NODETREE', expand=True)
		self.layout.prop(self, 'ao_samples', icon='ANIM_DATA')
		self.layout.prop(self, 'ao_hide_other', icon='VISIBLE_IPO_OFF')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		
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
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
	blur_strength = bpy.props.FloatProperty(name="ブラー強度", default=1, min=0.01, max=1, soft_min=0.01, soft_max=1, step=10, precision=2)
	blur_iterations = bpy.props.IntProperty(name="ブラー反復度", default=1, min=0, max=40, soft_min=0, soft_max=40)
	clean_angle = bpy.props.FloatProperty(name="ハイライト角度", default=3.14159, min=0, max=3.14159, soft_min=0, soft_max=3.14159, step=3, precision=0, subtype='ANGLE')
	dirt_angle = bpy.props.FloatProperty(name="擬似AO角度", default=0, min=0, max=3.14159, soft_min=0, soft_max=3.14159, step=3, precision=0, subtype='ANGLE')
	dirt_only = bpy.props.BoolProperty(name="擬似AOのみ", default=True)
	
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
		row.prop(self, 'blur_strength', icon='NONE', slider=True)
		row.prop(self, 'blur_iterations', icon='NONE')
		self.layout.prop(self, 'clean_angle', icon='NONE', slider=True)
		row = self.layout.row(align=True)
		row.prop(self, 'dirt_angle', icon='NONE', slider=True)
		row.prop(self, 'dirt_only', icon='FILE_TICK')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		pre_vertex_color_active_index = me.vertex_colors.active_index
		vertex_color = me.vertex_colors.new(name="quick_dirty_bake_image_temp")
		me.vertex_colors.active = vertex_color
		
		bpy.ops.paint.vertex_color_dirt(override, blur_strength=self.blur_strength, blur_iterations=self.blur_iterations, clean_angle=self.clean_angle, dirt_angle=self.dirt_angle, dirt_only=self.dirt_only)
		
		context.scene.render.bake_type = 'VERTEX_COLORS'
		context.scene.render.use_bake_selected_to_active = False
		
		bpy.ops.object.bake_image()
		
		me.vertex_colors.remove(vertex_color)
		me.vertex_colors.active_index = pre_vertex_color_active_index
		
		return {'FINISHED'}

class quick_hemi_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_hemi_bake_image'
	bl_label = "ヘミライト・ベイク"
	bl_description = "アクティブオブジェクトに素早くヘミライトの陰をベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
	lamp_energy = bpy.props.FloatProperty(name="光の強さ", default=1, min=0, max=2, soft_min=0, soft_max=2, step=50, precision=2)
	
	use_ao = bpy.props.BoolProperty(name="AOを使用", default=False)
	ao_samples = bpy.props.IntProperty(name="AOの精度", default=20, min=1, max=50, soft_min=1, soft_max=50)
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
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
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

class quick_shadow_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_shadow_bake_image'
	bl_label = "影・ベイク"
	bl_description = "アクティブオブジェクトに素早く影をベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
	lamp_max_angle = bpy.props.FloatProperty(name="光源の最大角度", default=0.5236, min=0, max=1.5708, soft_min=0, soft_max=1.5708, step=100, precision=0, subtype='ANGLE', unit='ROTATION')
	lamp_count = bpy.props.IntProperty(name="光源の数", default=8, min=1, max=20, soft_min=1, soft_max=20)
	is_shadow_only = bpy.props.BoolProperty(name="影のみ", default=False)
	
	@classmethod
	def poll(cls, context):
		if not len(context.selected_objects):
			return False
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if len(me.uv_layers):
					return True
		return False
	
	def invoke(self, context, event):
		self.image_name = context.active_object.name + " Shadow Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="光源設定", icon='LAMP_SUN')
		self.layout.prop(self, 'lamp_max_angle', icon='LAMP_AREA', slider=True)
		self.layout.prop(self, 'lamp_count', icon='LAMP_POINT')
		self.layout.prop(self, 'is_shadow_only', icon='IMAGE_ALPHA')
	
	def execute(self, context):
		import mathutils
		
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		hide_render_restore = common.hide_render_restore()
		material_restore = common.material_restore(ob)
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = context.blend_data.materials.new("quick_shadow_bake_image_temp")
		ob.material_slots[0].material = temp_mate
		
		if self.is_shadow_only:
			temp_hemi = context.blend_data.lamps.new("quick_hemi_bake_image_lamp_temp", 'HEMI')
			temp_hemi_ob = context.blend_data.objects.new("quick_hemi_bake_image_lamp_temp", temp_hemi)
			context.scene.objects.link(temp_hemi_ob)
			temp_hemi.energy = 0.00001
		
		new_lamps = []
		lamp_count = (self.lamp_count * 2) - 1
		angle_interval = self.lamp_max_angle / self.lamp_count
		for x_index in range(lamp_count):
			x_angle = angle_interval * (x_index - self.lamp_count + 1)
			
			for y_index in range(lamp_count):
				y_angle = angle_interval * (y_index - self.lamp_count + 1)
				
				temp_lamp = context.blend_data.lamps.new("quick_shadow_bake_image_temp", 'SUN')
				temp_lamp.shadow_method = 'RAY_SHADOW'
				temp_lamp_ob = context.blend_data.objects.new("quick_shadow_bake_image_temp", temp_lamp)
				context.scene.objects.link(temp_lamp_ob)
				temp_lamp_ob.rotation_mode = 'XYZ'
				temp_lamp_ob.rotation_euler = mathutils.Euler((x_angle, y_angle, 0), 'XYZ')
				
				new_lamps.append(temp_lamp)
				new_lamps.append(temp_lamp_ob)
		
		context.scene.render.bake_type = 'SHADOW'
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_mate] + new_lamps)
		if self.is_shadow_only: common.remove_data([temp_hemi_ob, temp_hemi])
		
		material_restore.restore()
		hide_render_restore.restore()
		
		return {'FINISHED'}

class quick_side_shadow_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_side_shadow_bake_image'
	bl_label = "側面陰・ベイク"
	bl_description = "アクティブオブジェクトに素早く側面陰をベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
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
		self.image_name = context.active_object.name + " SideShadow Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		material_restore = common.material_restore(ob)
		
		blend_path = os.path.join(os.path.dirname(__file__), "append_data.blend")
		with context.blend_data.libraries.load(blend_path) as (data_from, data_to):
			data_to.materials = ["Side Shadow"]
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = data_to.materials[0]
		ob.material_slots[0].material = temp_mate
		
		temp_lamp = context.blend_data.lamps.new("quick_side_shadow_bake_image_lamp_temp", 'HEMI')
		temp_lamp_ob = context.blend_data.objects.new("quick_side_shadow_bake_image_lamp_temp", temp_lamp)
		context.scene.objects.link(temp_lamp_ob)
		
		pre_scene_camera = context.scene.camera
		temp_camera = context.blend_data.cameras.new("quick_side_shadow_bake_image_camera_temp")
		temp_camera_ob = context.blend_data.objects.new("quick_side_shadow_bake_image_camera_temp", temp_camera)
		context.scene.objects.link(temp_camera_ob)
		temp_camera_ob.rotation_euler[0] = 1.5708
		context.scene.camera = temp_camera_ob
		
		context.scene.world.light_settings.use_ambient_occlusion = False
		
		context.scene.render.bake_type = 'FULL'
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_mate, temp_lamp_ob, temp_lamp, temp_camera_ob, temp_camera])
		context.scene.camera = pre_scene_camera
		
		material_restore.restore()
		
		return {'FINISHED'}

class quick_gradation_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_gradation_bake_image'
	bl_label = "グラデーション・ベイク"
	bl_description = "アクティブオブジェクトに素早くグラデーションをベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
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
		self.image_name = context.active_object.name + " SideShadow Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		temp_me = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='RENDER')
		zs = [(ob.matrix_world * v.co).z for v in temp_me.vertices]
		zs.sort()
		me_conter = (zs[0] + zs[-1]) / 2
		me_height = zs[-1] - zs[0]
		
		material_restore = common.material_restore(ob)
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = context.blend_data.materials.new("quick_gradation_bake_image_temp")
		ob.material_slots[0].material = temp_mate
		temp_slot = temp_mate.texture_slots.create(0)
		temp_tex = context.blend_data.textures.new("quick_gradation_bake_image_temp", 'BLEND')
		temp_slot.texture = temp_tex
		temp_tex.use_color_ramp = True
		temp_slot.mapping_y = 'Z'
		temp_slot.mapping_z = 'Y'
		temp_slot.texture_coords = 'GLOBAL'
		temp_tex.color_ramp.elements[0].color = (0, 0, 0, 1)
		temp_tex.use_flip_axis = 'VERTICAL'
		temp_slot.offset[1] = -me_conter
		temp_slot.scale[1] = 1 / (me_height / 2)
		
		context.scene.render.bake_type = 'TEXTURE'
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_me, temp_mate, temp_tex])
		
		material_restore.restore()
		
		return {'FINISHED'}

class quick_metal_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_metal_bake_image'
	bl_label = "金属・ベイク"
	bl_description = "アクティブオブジェクトに素早く金属風にベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
	mate_color = bpy.props.FloatVectorProperty(name="色", default=(1, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR')
	environment_strength = bpy.props.FloatProperty(name="映り込み強さ", default=1, min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2)
	
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
		self.image_name = context.active_object.name + " Metal Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="金属設定", icon='MATCAP_19')
		self.layout.prop(self, 'mate_color', icon='COLOR')
		self.layout.prop(self, 'environment_strength', icon='MATCAP_19', slider=True)
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		hide_render_restore = common.hide_render_restore()
		material_restore = common.material_restore(ob)
		
		blend_path = os.path.join(os.path.dirname(__file__), "append_data.blend")
		with context.blend_data.libraries.load(blend_path) as (data_from, data_to):
			data_to.materials = ["Metal"]
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = data_to.materials[0]
		ob.material_slots[0].material = temp_mate
		temp_mate.diffuse_color = self.mate_color[:]
		temp_mate.texture_slots[0].diffuse_color_factor = self.environment_strength
		
		temp_lamp = context.blend_data.lamps.new("quick_metal_bake_image_lamp_temp", 'HEMI')
		temp_lamp_ob = context.blend_data.objects.new("quick_metal_bake_image_lamp_temp", temp_lamp)
		context.scene.objects.link(temp_lamp_ob)
		#temp_lamp.energy = self.lamp_energy
		
		pre_scene_camera = context.scene.camera
		temp_camera = context.blend_data.cameras.new("quick_metal_bake_image_camera_temp")
		temp_camera_ob = context.blend_data.objects.new("quick_metal_bake_image_camera_temp", temp_camera)
		context.scene.objects.link(temp_camera_ob)
		temp_camera_ob.rotation_euler[0] = 1.5708
		context.scene.camera = temp_camera_ob
		
		context.scene.world.light_settings.use_ambient_occlusion = False
		
		context.scene.render.bake_type = 'FULL'
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_mate, temp_lamp_ob, temp_lamp, temp_camera_ob, temp_camera])
		context.scene.camera = pre_scene_camera
		
		material_restore.restore()
		hide_render_restore.restore()
		
		return {'FINISHED'}

class quick_hair_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_hair_bake_image'
	bl_label = "ヘアー・ベイク"
	bl_description = "アクティブオブジェクトに素早くCM3D2の髪風のテクスチャをベイクします"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	items = [
		('128', "128 px", "", 'LAYER_USED', 1),
		('256', "256 px", "", 'LAYER_ACTIVE', 2),
		('512', "512 px", "", 'HAND', 3),
		('1024', "1024 px", "", 'FILE_TICK', 4),
		('2048', "2048 px", "", 'ERROR', 5),
		('4096', "4096 px", "", 'CANCEL', 6),
		]
	image_width = bpy.props.EnumProperty(items=items, name="幅", default='1024')
	image_height = bpy.props.EnumProperty(items=items, name="高", default='1024')
	
	mate_diffuse_color = bpy.props.FloatVectorProperty(name="髪色", default=(1, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=3)
	mate_angel_ring_factor = bpy.props.FloatProperty(name="天使の輪の強さ", default=0.5, min=0, max=1, soft_min=0, soft_max=1, step=50, precision=2)
	
	lamp_energy = bpy.props.FloatProperty(name="光の強さ", default=1, min=0, max=2, soft_min=0, soft_max=2, step=50, precision=2)
	
	use_ao = bpy.props.BoolProperty(name="AOを使用", default=False)
	ao_samples = bpy.props.IntProperty(name="AOの精度", default=20, min=1, max=50, soft_min=1, soft_max=50)
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
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		
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
