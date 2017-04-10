# 「プロパティ」エリア → 「レンダー」タブ → 「ベイク」パネル
import os, re, sys, bpy, time, numpy, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	col = self.layout.column(align=True)
	col.label(text="CM3D2用ベイク", icon_value=common.preview_collections['main']['KISS'].icon_id)
	row = col.row(align=True)
	row.operator('object.add_bake_image', icon='IMAGE_COL', text="新規画像")
	row.operator('object.quick_ao_bake_image', icon='BRUSH_TEXFILL', text="AO (重)")
	row.operator('object.quick_dirty_bake_image', icon='MATSPHERE', text="擬似AO")
	row = col.row(align=True)
	row.operator('object.quick_hemi_bake_image', icon='LAMP_HEMI', text="ヘミライト")
	row.operator('object.quick_shadow_bake_image', icon='IMAGE_ALPHA', text="影 (重)")
	row.operator('object.quick_side_shadow_bake_image', icon='ARROW_LEFTRIGHT', text="側面陰")
	row = col.row(align=True)
	row.operator('object.quick_gradation_bake_image', icon='MESH_PLANE', text="グラデーション")
	row.operator('object.quick_uv_border_bake_image', icon='MATCAP_24', text="UV縁")
	row.operator('object.quick_mesh_border_bake_image', icon='EDIT_VEC', text="メッシュ縁")
	row = col.row(align=True)
	row.operator('object.quick_density_bake_image', icon='STICKY_UVS_LOC', text="密度")
	row.operator('object.quick_bulge_bake_image', icon='BRUSH_INFLATE', text="膨らみ")
	row.operator('object.quick_mesh_distance_bake_image', icon='RETOPO', text="メッシュ間距離")
	row = col.row(align=True)
	row.operator('object.quick_metal_bake_image', icon='MATCAP_19', text="金属")
	row.operator('object.quick_hair_bake_image', icon='PARTICLEMODE', text="髪")
	row.operator('object.quick_semen_bake_image', icon='MOD_FLUIDSIM', text="白い液体")

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
		ob.hide_render = False
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
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
		ob.hide_render = False
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		context.scene.world.light_settings.gather_method = self.ao_gather_method
		context.scene.world.light_settings.samples = self.ao_samples
		
		if self.ao_hide_other: hide_render_restore = common.hide_render_restore()
		
		context.scene.render.bake_type = 'AO'
		context.scene.render.use_bake_normalize = True
		context.scene.render.use_bake_selected_to_active = False
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
		self.image_name = ob.name + " Dirty AO Bake"
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
		ob.select = False
		ob.hide_render = False
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		temp_me = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')
		temp_ob = context.blend_data.objects.new("quick_dirty_bake_image_temp", temp_me)
		context.scene.objects.link(temp_ob)
		for vc in temp_me.vertex_colors:
			temp_me.vertex_colors.remove(vc)
		temp_vertex_color = temp_me.vertex_colors.new(name="quick_dirty_bake_image_temp")
		context.scene.objects.active = temp_ob
		temp_ob.select = True
		
		override = context.copy()
		override['object'] = temp_ob
		bpy.ops.paint.vertex_color_dirt(override, blur_strength=self.blur_strength, blur_iterations=self.blur_iterations, clean_angle=self.clean_angle, dirt_angle=self.dirt_angle, dirt_only=self.dirt_only)
		
		temp_ob.update_tag(refresh={'OBJECT', 'DATA'})
		context.scene.render.bake_type = 'VERTEX_COLORS'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image(context.copy())
		
		common.remove_data([temp_me, temp_ob])
		context.scene.objects.active = ob
		ob.select = True
		
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
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
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
		context.scene.render.use_bake_selected_to_active = False
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
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
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
		context.scene.render.use_bake_selected_to_active = False
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
	
	is_bipolarization = bpy.props.BoolProperty(name="二極化を有効", default=True)
	bipolarization_threshold = bpy.props.FloatProperty(name="二極化のしきい値", default=0.5, min=0, max=1, soft_min=0, soft_max=1, step=5, precision=2)
	bipolarization_blur = bpy.props.FloatProperty(name="二極化のぼかし", default=0.05, min=0, max=1, soft_min=0, soft_max=1, step=1, precision=2)
	
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
		self.image_name = context.active_object.name + " SideShade Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.separator()
		self.layout.prop(self, 'is_bipolarization', icon='IMAGE_ALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'bipolarization_threshold', icon='NONE', text="しきい値")
		row.prop(self, 'bipolarization_blur', icon='NONE', text="ぼかし")
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True, float_buffer=True)
		
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
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_mate, temp_lamp_ob, temp_lamp, temp_camera_ob, temp_camera])
		context.scene.camera = pre_scene_camera
		
		material_restore.restore()
		
		if self.is_bipolarization:
			img_w, img_h, img_c = img.size[0], img.size[1], img.channels
			pixels = numpy.array(img.pixels).reshape(img_h, img_w, img_c)
			min = self.bipolarization_threshold - (self.bipolarization_blur / 2.0)
			max = self.bipolarization_threshold + (self.bipolarization_blur / 2.0)
			i = numpy.where(pixels[:,:,:3] <= min)
			pixels[:,:,:3][i] = 0.0
			i = numpy.where(max <= pixels[:,:,:3])
			pixels[:,:,:3][i] = 1.0
			if 0.0 < max - min:
				i = numpy.where((min < pixels[:,:,:3]) & (pixels[:,:,:3] < max))
				pixels[:,:,:3][i] -= min
				pixels[:,:,:3][i] *= 1.0 / (max - min)
			img.pixels = pixels.flatten()
		
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
		self.image_name = context.active_object.name + " Gradation Bake"
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
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		temp_me = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')
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
		context.scene.render.use_bake_selected_to_active = False
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
	
	mate_color = bpy.props.FloatVectorProperty(name="色", default=(0.22, 0.22, 0.22), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR')
	environment_strength = bpy.props.FloatProperty(name="映り込み強さ", default=1, min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2)
	highlight_strength = bpy.props.FloatProperty(name="ハイライト強さ", default=0.5, min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2)
	
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
		row = self.layout.row(align=True)
		row.prop(self, 'environment_strength', icon='MATCAP_19', slider=True)
		row.prop(self, 'highlight_strength', icon='MATCAP_09', slider=True)
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
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
		temp_mate.node_tree.nodes["Mix.001"].inputs[0].default_value = 1.0 - self.highlight_strength
		
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
		context.scene.render.use_bake_selected_to_active = False
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
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
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
		
		
		blend_path = os.path.join(os.path.dirname(__file__), "append_data.blend")
		with context.blend_data.libraries.load(blend_path) as (data_from, data_to):
			data_to.materials = ["CM3D2 Hair"]
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = data_to.materials[0]
		ob.material_slots[0].material = temp_mate
		
		temp_mate.diffuse_color = self.mate_diffuse_color
		temp_mate.node_tree.nodes["mate_angel_ring_factor"].inputs[0].default_value = self.mate_angel_ring_factor
		
		context.scene.world.light_settings.use_ambient_occlusion = self.use_ao
		if self.use_ao:
			context.scene.world.light_settings.samples = self.ao_samples
			context.scene.world.light_settings.ao_blend_type = 'MULTIPLY'
		
		context.scene.render.bake_type = 'FULL'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		temp_tex = temp_mate.texture_slots[0].texture
		
		common.remove_data([temp_mate, temp_tex, temp_camera_ob, temp_camera, temp_lamp_ob, temp_lamp])
		context.scene.camera = pre_scene_camera
		
		material_restore.restore()
		if self.ao_hide_other: hide_render_restore.restore()
		
		return {'FINISHED'}

class quick_uv_border_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_uv_border_bake_image'
	bl_label = "UV縁・ベイク"
	bl_description = "アクティブオブジェクトに素早くUVの縁を黒くベイクします"
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
		('FLAT', "フラット", "", 'IPO_CONSTANT', 1),
		('TENT', "テント", "", 'IPO_LINEAR', 2),
		('QUAD', "二次式", "", 'IPO_QUAD', 3),
		('CUBIC', "三次式", "", 'IPO_CUBIC', 4),
		('GAUSS', "ガウシアン", "", 'HAND', 5),
		('FAST_GAUSS', "高速ガウシアン", "", 'ALIASED', 6),
		('CATROM', "Catrom", "", 'FILE_TICK', 7),
		('MITCH', "Mitch", "", 'FILE_TICK', 8),
		]
	blur_type = bpy.props.EnumProperty(items=items, name="ぼかしタイプ", default='GAUSS')
	blur_strength = bpy.props.IntProperty(name="ぼかし強度", default=100, min=0, max=1000, soft_min=0, soft_max=1000)
	normalize = bpy.props.BoolProperty(name="正規化", default=True)
	keep_alpha = bpy.props.BoolProperty(name="余白を透過", default=True)
	
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
		self.image_name = ob.name + " UV Border Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="縁設定", icon='MATCAP_24')
		self.layout.prop(self, 'blur_type', icon='BRUSH_BLUR')
		self.layout.prop(self, 'blur_strength', icon='ARROW_LEFTRIGHT')
		row = self.layout.row(align=True)
		row.prop(self, 'normalize', icon='IMAGE_ALPHA')
		row.prop(self, 'keep_alpha', icon='IMAGE_RGB_ALPHA')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		
		img.generated_color = (0, 0, 0, 1)
		
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		material_restore = common.material_restore(ob)
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = context.blend_data.materials.new("quick_gradation_bake_image_temp")
		ob.material_slots[0].material = temp_mate
		temp_mate.diffuse_color = (1, 1, 1)
		
		pre_use_bake_clear = context.scene.render.use_bake_clear
		pre_bake_margin = context.scene.render.bake_margin
		context.scene.render.use_bake_clear = False
		context.scene.render.bake_type = 'TEXTURE'
		context.scene.render.use_bake_selected_to_active = False
		
		bpy.ops.object.bake_image()
		img_w, img_h, img_c = img.size[0], img.size[1], img.channels
		pixels = numpy.array(img.pixels).reshape(img_h, img_w, img_c)
		img_alphas = pixels[:,:,0]
		
		img.reload()
		context.scene.render.bake_margin = 0
		bpy.ops.object.bake_image()
		
		context.scene.render.use_bake_clear = pre_use_bake_clear
		context.scene.render.bake_margin = pre_bake_margin
		
		# 無駄に壮大なぼかし処理
		pre_resolution_x = context.scene.render.resolution_x
		pre_resolution_y = context.scene.render.resolution_y
		pre_resolution_percentage = context.scene.render.resolution_percentage
		context.scene.render.resolution_x = img.size[0]
		context.scene.render.resolution_y = img.size[1]
		context.scene.render.resolution_percentage = 100
		
		context.scene.use_nodes = True
		node_tree = context.scene.node_tree
		for node in node_tree.nodes:
			node_tree.nodes.remove(node)
		
		img_node = node_tree.nodes.new('CompositorNodeImage')
		img_node.location = (0, 0)
		img_node.image = img
		
		blur_node = node_tree.nodes.new('CompositorNodeBlur')
		blur_node.location = (250, 0)
		blur_node.size_x, blur_node.size_y = 1, 1
		blur_node.filter_type = self.blur_type
		blur_node.inputs[1].default_value = self.blur_strength
		
		out_node = node_tree.nodes.new('CompositorNodeComposite')
		out_node.location = (500, 0)
		
		node_tree.links.new(blur_node.inputs[0], img_node.outputs[0])
		node_tree.links.new(out_node.inputs[0], blur_node.outputs[0])
		
		bpy.ops.render.render()
		
		render_img = context.blend_data.images["Render Result"]
		
		temp_png_path = os.path.join(bpy.app.tempdir, "temp.png")
		img_override = context.copy()
		img_override['object'] = render_img
		img_override['edit_image'] = render_img
		img_override['area'] = area
		common.set_area_space_attr(area, 'image', render_img)
		bpy.ops.image.save_as(img_override, save_as_render=True, copy=True, filepath=temp_png_path, relative_path=False, show_multiview=False, use_multiview=False)
		img.source = 'FILE'
		img.filepath = temp_png_path
		img.reload()
		pixels = numpy.array(img.pixels).reshape(img_h, img_w, img_c)
		if self.keep_alpha:
			pixels[:,:,3] = img_alphas
		if self.normalize:
			pixels[:,:,:3] -= 0.5
			pixels[:,:,:3] *= 2.0
		img.pixels = pixels.flatten()
		img.pack(as_png=True)
		os.remove(temp_png_path)
		
		for node in node_tree.nodes:
			node_tree.nodes.remove(node)
		context.scene.use_nodes = False
		context.scene.render.resolution_x = pre_resolution_x
		context.scene.render.resolution_y = pre_resolution_y
		context.scene.render.resolution_percentage = pre_resolution_percentage
		# 無駄に壮大なぼかし処理 完
		
		common.set_area_space_attr(area, 'image', img)
		common.remove_data([temp_mate])
		material_restore.restore()
		
		return {'FINISHED'}

class quick_mesh_border_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_mesh_border_bake_image'
	bl_label = "メッシュ縁・ベイク"
	bl_description = "アクティブオブジェクトに素早くメッシュの縁を黒くベイクします"
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
	
	range = bpy.props.IntProperty(name="範囲", default=5, min=1, max=50, soft_min=1, soft_max=50)
	
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
		self.image_name = ob.name + " Mesh Border Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		
		self.layout.prop(self, 'range', icon='PROP_ON')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob.select = False
		ob.hide_render = False
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		temp_me = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')
		temp_ob = context.blend_data.objects.new("quick_density_bake_image", temp_me)
		context.scene.objects.link(temp_ob)
		for vc in temp_me.vertex_colors:
			temp_me.vertex_colors.remove(vc)
		temp_vertex_color = temp_me.vertex_colors.new(name="quick_density_bake_image")
		context.scene.objects.active = temp_ob
		temp_ob.select = True
		
		def paint_selected_vertices(me, color, except_indices=[]):
			paint_vertices = []
			for vert in me.vertices:
				if vert.select and vert.index not in except_indices:
					paint_vertices.append(vert.index)
			for loop in me.loops:
				if loop.vertex_index in paint_vertices:
					me.vertex_colors.active.data[loop.index].color = color
			return paint_vertices
		
		context.tool_settings.mesh_select_mode = (True, False, False)
		already_vert_indices = []
		for index in range(self.range):
			bpy.ops.object.mode_set(mode='EDIT')
			if index == 0:
				bpy.ops.mesh.reveal()
				bpy.ops.mesh.select_all(action='DESELECT')
				bpy.ops.mesh.select_non_manifold()
			else:
				bpy.ops.mesh.select_more()
			bpy.ops.object.mode_set(mode='OBJECT')
			
			value = (1.0 / self.range) * index
			already_vert_indices += paint_selected_vertices(temp_me, [value, value, value], already_vert_indices)
		
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='DESELECT')
		bpy.ops.object.mode_set(mode='OBJECT')
		
		context.scene.render.bake_type = 'VERTEX_COLORS'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_me, temp_ob])
		context.scene.objects.active = ob
		ob.select = True
		
		return {'FINISHED'}

class quick_density_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_density_bake_image'
	bl_label = "密度・ベイク"
	bl_description = "アクティブオブジェクトに素早く密度をベイクします"
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
		('ALL', "全て", "", 'MOD_SUBSURF', 1),
		('PARTS', "パーツごと", "", 'GROUP_VCOL', 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="比較対象", default='PARTS')
	
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
		self.image_name = ob.name + " Density Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		self.layout.label(text="比較対象", icon='ZOOM_PREVIOUS')
		self.layout.prop(self, 'mode', icon='ZOOM_PREVIOUS', expand=True)
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob.select = False
		ob.hide_render = False
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		temp_me = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')
		temp_ob = context.blend_data.objects.new("quick_density_bake_image", temp_me)
		context.scene.objects.link(temp_ob)
		for vc in temp_me.vertex_colors:
			temp_me.vertex_colors.remove(vc)
		temp_vertex_color = temp_me.vertex_colors.new(name="quick_density_bake_image")
		context.scene.objects.active = temp_ob
		temp_ob.select = True
		
		bm = bmesh.new()
		bm.from_mesh(temp_me)
		bm.verts.ensure_lookup_table()
		
		vert_islands = []
		if self.mode == 'ALL':
			vert_islands.append([v.index for v in bm.verts])
		elif self.mode == 'PARTS':
			alread_vert_indices = []
			for i in range(9**9):
				
				vert_islands.append([])
				
				for vert in bm.verts:
					if vert.index not in alread_vert_indices:
						new_verts = [vert]
						alread_vert_indices.append(vert.index)
						vert_islands[-1].append(vert.index)
						break
				
				for j in range(9**9):
					
					vs = []
					for vert in new_verts:
						for edge in vert.link_edges:
							for v in edge.verts:
								if vert.index != v.index and v.index not in alread_vert_indices:
									vs.append(v)
									alread_vert_indices.append(v.index)
									vert_islands[-1].append(v.index)
									break
					
					if not len(vs):
						break
					
					new_verts = vs[:]
				
				if len(bm.verts) <= len(alread_vert_indices):
					break
		
		for island in vert_islands:
			edge_lens = []
			for index in island:
				lens = [e.calc_length() for e in bm.verts[index].link_edges]
				edge_lens.append( sum(lens) / len(lens) )
			edge_min, edge_max = min(edge_lens), max(edge_lens)
			try:
				multi = 1.0 / (edge_max - edge_min)
			except:
				multi = 1.0
			
			for index in island:
				vert = bm.verts[index]
				
				lens = [e.calc_length() for e in vert.link_edges]
				l = sum(lens) / len(lens)
				value = (l - edge_min) * multi
				for loop in vert.link_loops:
					temp_vertex_color.data[loop.index].color = (value, value, value)
		
		context.scene.render.bake_type = 'VERTEX_COLORS'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_me, temp_ob])
		context.scene.objects.active = ob
		ob.select = True
		
		return {'FINISHED'}

class quick_mesh_distance_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_mesh_distance_bake_image'
	bl_label = "メッシュ間距離・ベイク"
	bl_description = "アクティブオブジェクトに他オブジェクトとの距離をベイクします"
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
		obs = context.selected_objects
		if len(obs) != 2: return False
		for ob in obs:
			if ob.type != 'MESH':
				return False
		me = context.active_object.data
		if len(me.uv_layers):
			return True
		return False
	
	def invoke(self, context, event):
		ob = context.active_object
		self.image_name = ob.name + " Mesh Distance Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
	
	def execute(self, context):
		target_ob = context.active_object
		target_ob.hide_render = False
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
			ob.select = False
		target_me = target_ob.data
		source_me = source_ob.data
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in target_me.uv_textures.active.data:
			elem.image = img
		
		temp_me = target_ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')
		temp_ob = context.blend_data.objects.new("quick_density_bake_image", temp_me)
		context.scene.objects.link(temp_ob)
		for vc in temp_me.vertex_colors:
			temp_me.vertex_colors.remove(vc)
		temp_vertex_color = temp_me.vertex_colors.new(name="quick_density_bake_image")
		context.scene.objects.active = temp_ob
		temp_ob.select = True
		
		bvh = mathutils.bvhtree.BVHTree.FromObject(source_ob, context.scene)
		
		vert_dists = []
		for vert in temp_me.vertices:
			co = target_ob.matrix_world * vert.co
			location, normal, index, dist = bvh.find(co)
			vert_dists.append(dist)
		
		dist_min, dist_max = min(vert_dists), max(vert_dists)
		try:
			multi = 1.0 / (dist_max - dist_min)
		except:
			multi = 1.0
		
		for loop in temp_me.loops:
			value = ( vert_dists[loop.vertex_index] - dist_min ) * multi
			temp_vertex_color.data[loop.index].color = (value, value, value)
		
		context.scene.render.bake_type = 'VERTEX_COLORS'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_me, temp_ob])
		context.scene.objects.active = target_ob
		target_ob.select = True
		source_ob.select = True
		
		return {'FINISHED'}

class quick_bulge_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_bulge_bake_image'
	bl_label = "膨らみ・ベイク"
	bl_description = "アクティブオブジェクトに膨らんでいる部分を白くベイクします"
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
		ob = context.active_object
		self.image_name = ob.name + " Bulge Bake"
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
		ob.select = False
		ob.hide_render = False
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		temp_me = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')
		temp_ob = context.blend_data.objects.new("quick_bulge_bake_image", temp_me)
		context.scene.objects.link(temp_ob)
		for vc in temp_me.vertex_colors:
			temp_me.vertex_colors.remove(vc)
		temp_vertex_color = temp_me.vertex_colors.new(name="quick_bulge_bake_image")
		context.scene.objects.active = temp_ob
		temp_ob.select = True
		
		bm = bmesh.new()
		bm.from_mesh(temp_me)
		
		angles = []
		for vert in bm.verts:
			normal = vert.normal
			edge_angle_total = 0.0
			for edge in vert.link_edges:
				diff_co = edge.other_vert(vert).co - vert.co
				if 0 < diff_co.length:
					edge_angle_total += normal.angle(diff_co)
			if len(vert.link_edges):
				edge_angle = edge_angle_total / len(vert.link_edges)
			else:
				edge_angle = 0.0
			angles.append(edge_angle)
		
		angle_min, angle_max = 1.5708, max(angles)
		multi = 1.0 / (angle_max - angle_min)
		
		for vert in bm.verts:
			value = (angles[vert.index] - angle_min) * multi
			for loop in vert.link_loops:
				temp_vertex_color.data[loop.index].color = (value, value, value)
		
		context.scene.render.bake_type = 'VERTEX_COLORS'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_me, temp_ob])
		context.scene.objects.active = ob
		ob.select = True
		
		return {'FINISHED'}

class quick_semen_bake_image(bpy.types.Operator):
	bl_idname = 'object.quick_semen_bake_image'
	bl_label = "白い液体・ベイク"
	bl_description = "アクティブオブジェクトに白い液体をベイクします"
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
	
	texture_scale = bpy.props.FloatProperty(name="テクスチャサイズ", default=1, min=0, max=100, soft_min=0, soft_max=100, step=50, precision=1)
	
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
		self.image_name = ob.name + " Semen Bake"
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="新規画像設定", icon='IMAGE_COL')
		self.layout.prop(self, 'image_name', icon='SORTALPHA')
		row = self.layout.row(align=True)
		row.prop(self, 'image_width', icon='ARROW_LEFTRIGHT')
		row.prop(self, 'image_height', icon='NLA_PUSHDOWN')
		
		self.layout.prop(self, 'texture_scale', icon='TEXTURE')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob.hide_render = False
		
		override = context.copy()
		override['object'] = ob
		
		image_width, image_height = int(self.image_width), int(self.image_height)
		
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			img = context.blend_data.images.new(self.image_name, image_width, image_height, alpha=True)
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		for elem in me.uv_textures.active.data:
			elem.image = img
		
		material_restore = common.material_restore(ob)
		
		blend_path = os.path.join(os.path.dirname(__file__), "append_data.blend")
		with context.blend_data.libraries.load(blend_path) as (data_from, data_to):
			data_to.materials = ["精液"]
		
		bpy.ops.object.material_slot_add(override)
		temp_mate = data_to.materials[0]
		ob.material_slots[0].material = temp_mate
		temp_mate.texture_slots[0].scale = (self.texture_scale, self.texture_scale, self.texture_scale)
		
		context.scene.render.bake_type = 'TEXTURE'
		context.scene.render.use_bake_selected_to_active = False
		bpy.ops.object.bake_image()
		
		common.remove_data([temp_mate, temp_mate.texture_slots[0].texture, temp_mate.texture_slots[0].texture.image])
		
		material_restore.restore()
		
		return {'FINISHED'}
