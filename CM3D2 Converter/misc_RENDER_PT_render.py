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
	
	items = [
		('FACE_TEXTURE', "面のテクスチャでレンダリング", "", 'FACESEL_HLT', 1),
		('NOW_MATERIAL', "今のマテリアルでレンダリング", "", 'MATERIAL', 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="モード", default='FACE_TEXTURE')
	
	use_freestyle = bpy.props.BoolProperty(name="輪郭線を描画", default=True)
	line_thickness = bpy.props.FloatProperty(name="線の太さ", default=0.2, min=0, max=0.5, soft_min=0, soft_max=0.5, step=10, precision=2, subtype='PIXEL')
	line_color = bpy.props.FloatVectorProperty(name="線の色", default=(0, 0, 0), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=3)
	
	resolution = bpy.props.IntProperty(name="解像度", default=80, min=10, max=150, soft_min=10, soft_max=150, subtype='PIXEL')
	camera_angle = bpy.props.FloatVectorProperty(name="カメラ角度", default=(0.576667, 0.576667, 0.578715), min=-10, max=10, soft_min=-10, soft_max=10, step=1, precision=2, subtype='DIRECTION', size=3)
	camera_move = bpy.props.FloatVectorProperty(name="カメラ移動", default=(0, 0), min=-10, max=10, soft_min=-10, soft_max=10, step=10, precision=2, subtype='XYZ', size=2)
	zoom_multi = bpy.props.IntProperty(name="ズーム倍率", default=100, min=10, max=190, soft_min=10, soft_max=190, step=10, subtype='PERCENTAGE')
	
	use_background_color = bpy.props.BoolProperty(name="背景を使用", default=True)
	background_color = bpy.props.FloatVectorProperty(name="背景色", default=(1, 1, 1), min=0, max=1, soft_min=0, soft_max=1, step=10, precision=2, subtype='COLOR', size=3)
	
	@classmethod
	def poll(cls, context):
		obs = context.selected_objects
		if not len(obs):
			return False
		for ob in obs:
			if ob.type == 'MESH':
				return True
		return False
	
	def invoke(self, context, event):
		obs = context.selected_objects
		for ob in obs:
			if ob.type != 'MESH': continue
			me = ob.data
			if not len(me.uv_textures): continue
			if me.uv_textures.active.data[0].image:
				self.mode = 'FACE_TEXTURE'
				break
		else:
			self.mode = 'NOW_MATERIAL'
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'resolution', icon='IMAGE_COL', slider=True)
		self.layout.prop(self, 'mode', icon='TEXTURE_SHADED')
		self.layout.separator()
		
		row = self.layout.split(percentage=1/3, align=True)
		row.prop(self, 'use_freestyle', icon='LINE_DATA')
		row.prop(self, 'line_thickness', icon='ARROW_LEFTRIGHT', slider=True, text="太")
		row.prop(self, 'line_color', icon='COLOR', text="")
		self.layout.separator()
		
		col = self.layout.column(align=True)
		col.label(text="カメラ角度", icon='FILE_REFRESH')
		col.prop(self, 'camera_angle', text="")
		self.layout.prop(self, 'camera_move', icon='ARROW_LEFTRIGHT')
		self.layout.prop(self, 'zoom_multi', icon='VIEWZOOM', slider=True)
		self.layout.separator()
		
		row = self.layout.split(percentage=0.5, align=True)
		row.prop(self, 'use_background_color', icon='WORLD')
		row.prop(self, 'background_color', icon='COLOR', text="")
	
	def execute(self, context):
		import math, mathutils
		
		override = context.copy()
		
		obs = context.selected_objects
		
		if self.mode == 'FACE_TEXTURE':
			material_restores = []
			temp_mates = []
			for ob in obs:
				material_restores.append( common.material_restore(ob) )
				override['object'] = ob
				bpy.ops.object.material_slot_add(override)
				temp_mate = context.blend_data.materials.new("temp")
				ob.material_slots[0].material = temp_mate
				temp_mate.use_shadeless = True
				temp_mate.use_face_texture = True
				temp_mates.append(temp_mate)
		elif self.mode == 'NOW_MATERIAL':
			pre_mate_settings = []
			for ob in obs:
				pre_mate_settings.append([])
				for slot in ob.material_slots:
					if not slot.material: continue
					mate = slot.material
					pre_mate_settings[-1].append([mate, mate.use_shadeless])
					mate.use_shadeless = True
		
		xs, ys, zs = [], [], []
		for ob in obs:
			if ob.type == 'MESH':
				for vert in ob.data.vertices:
					co = ob.matrix_world * vert.co
					xs.append(co.x)
					ys.append(co.y)
					zs.append(co.z)
		xs.sort(), ys.sort(), zs.sort()
		center_co = mathutils.Vector((0, 0, 0))
		center_co.x = (xs[0] + xs[-1]) / 2.0
		center_co.y = (ys[0] + ys[-1]) / 2.0
		center_co.z = (zs[0] + zs[-1]) / 2.0
		
		hide_render_restore = common.hide_render_restore()
		
		maxs = [-999, -999, -999]
		mins = [999, 999, 999]
		for ob in obs:
			for i in range(8):
				for j in range(3):
					v = ob.bound_box[i][j]
					if maxs[j] < v:
						maxs[j] = v
					if v < mins[j]:
						mins[j] = v
		
		lens = [maxs[0] - mins[0]]
		lens.append(maxs[1] - mins[1])
		lens.append(maxs[2] - mins[2])
		lens.sort()
		zoom = lens[-1] * 1.2
		
		pre_scene_camera = context.scene.camera
		temp_camera = context.blend_data.cameras.new("render_cm3d2_icon_temp")
		temp_camera_ob = context.blend_data.objects.new("render_cm3d2_icon_temp", temp_camera)
		context.scene.objects.link(temp_camera_ob)
		context.scene.camera = temp_camera_ob
		temp_camera.type = 'ORTHO'
		temp_camera.ortho_scale = zoom * (self.zoom_multi * 0.01)
		
		direct = self.camera_angle.copy()
		direct.rotate( mathutils.Euler((math.radians(90), 0, 0), 'XYZ') )
		temp_camera_ob.rotation_mode = 'QUATERNION'
		temp_camera_ob.rotation_quaternion = direct.to_track_quat('Z', 'Y')
		temp_camera_ob.location = direct * 10
		temp_camera_ob.location += center_co
		vec = mathutils.Vector()
		vec.x, vec.y = -self.camera_move.x, -self.camera_move.y
		temp_camera_ob.location += direct.to_track_quat('Z', 'Y') * vec
		
		context.scene.render.resolution_x = self.resolution
		context.scene.render.resolution_y = self.resolution
		context.scene.render.resolution_percentage = 100
		
		context.scene.world.light_settings.use_ambient_occlusion = False
		context.scene.world.light_settings.ao_blend_type = 'ADD'
		context.scene.world.light_settings.gather_method = 'RAYTRACE'
		context.scene.world.light_settings.samples = 10
		
		context.scene.render.alpha_mode = 'SKY' if self.use_background_color else 'TRANSPARENT'
		context.scene.world.horizon_color = self.background_color
		
		if self.use_freestyle:
			pre_use_freestyle = context.scene.render.use_freestyle
			pre_line_thickness = context.scene.render.line_thickness
			context.scene.render.use_freestyle = True
			context.scene.render.line_thickness = self.line_thickness
			temp_lineset = context.scene.render.layers.active.freestyle_settings.linesets.new("temp")
			temp_lineset.linestyle.color = self.line_color
		
		bpy.ops.render.render()
		
		if self.use_freestyle:
			context.scene.render.use_freestyle = pre_use_freestyle
			context.scene.render.line_thickness = pre_line_thickness
			common.remove_data([temp_lineset.linestyle])
			context.scene.render.layers.active.freestyle_settings.linesets.remove(temp_lineset)
		
		img = context.blend_data.images["Render Result"]
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		common.set_area_space_attr(area, 'image', img)
		
		common.remove_data([temp_camera_ob, temp_camera])
		context.scene.camera = pre_scene_camera
		
		if self.mode == 'FACE_TEXTURE':
			for material_restore in material_restores:
				material_restore.restore()
			common.remove_data(temp_mates)
		elif self.mode == 'NOW_MATERIAL':
			for ob_mate in pre_mate_settings:
				for mate, is_shadeless in ob_mate:
					mate.use_shadeless = is_shadeless
		
		hide_render_restore.restore()
		
		return {'FINISHED'}
