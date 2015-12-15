import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	self.layout.operator('render.render_cm3d2_icon', icon_value=common.preview_collections['main']['KISS'].icon_id)

class render_cm3d2_icon(bpy.types.Operator):
	bl_idname = 'render.render_cm3d2_icon'
	bl_label = "CM3D2メニュー用のアイコンをレンダリング"
	bl_description = "CM3D2内のアイコン画像に使用できそうな画像をレンダリングします"
	bl_options = {'REGISTER', 'UNDO'}
	
	zoom = bpy.props.FloatProperty(name="ズーム", default=5, min=0.1, max=10, soft_min=0.1, soft_max=10, step=20, precision=2)
	resolution_percentage = bpy.props.IntProperty(name="解像度倍率", default=100, min=50, max=200, soft_min=50, soft_max=200, step=10, subtype='PERCENTAGE')
	
	@classmethod
	def poll(cls, context):
		obs = context.selected_objects
		if not len(obs):
			return False
		for ob in obs:
			if ob.type != 'MESH':
				return False
		return True
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'zoom', icon='VIEWZOOM', slider=True)
		self.layout.prop(self, 'resolution_percentage', icon='IMAGE_COL', slider=True)
	
	def execute(self, context):
		import mathutils
		
		obs = context.selected_objects
		
		locs = mathutils.Vector((0, 0, 0))
		locs_count = 0
		for ob in obs:
			for vert in ob.data.vertices:
				locs += ob.matrix_world * vert.co
			locs_count += len(ob.data.vertices)
		center_co = locs / locs_count
		
		hided_objects = []
		for o in context.blend_data.objects:
			for b, i in enumerate(context.scene.layers):
				if o.layers[i] and b and ob.name != o.name and not o.hide_render:
					hided_objects.append(o)
					o.hide_render = True
					break
		
		pre_scene_camera = context.scene.camera
		temp_camera = context.blend_data.cameras.new("render_cm3d2_icon_temp")
		temp_camera_ob = context.blend_data.objects.new("render_cm3d2_icon_temp", temp_camera)
		context.scene.objects.link(temp_camera_ob)
		context.scene.camera = temp_camera_ob
		temp_camera.type = 'ORTHO'
		temp_camera.ortho_scale = self.zoom
		temp_camera_ob.rotation_euler = (0.954696, 0, 0.785398)
		temp_camera_ob.location = (10, -10, 10)
		temp_camera_ob.location += center_co
		
		context.scene.render.resolution_x = 80
		context.scene.render.resolution_y = 80
		context.scene.render.resolution_percentage = self.resolution_percentage
		
		context.scene.world.light_settings.use_ambient_occlusion = True
		context.scene.world.light_settings.ao_blend_type = 'ADD'
		context.scene.world.light_settings.gather_method = 'RAYTRACE'
		context.scene.world.light_settings.samples = 10
		context.scene.render.alpha_mode = 'TRANSPARENT'
		
		bpy.ops.render.render()
		
		img = context.blend_data.images["Render Result"]
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			for space in area.spaces:
				if space.type == 'IMAGE_EDITOR':
					space.image = img
					break
		
		common.remove_data([temp_camera_ob, temp_camera])
		context.scene.camera = pre_scene_camera
		
		for o in hided_objects:
			o.hide_render = False
		
		return {'FINISHED'}
