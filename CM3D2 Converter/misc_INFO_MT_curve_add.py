import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	self.layout.separator()
	self.layout.operator('curve.hair_bunch_add', text="髪の房", icon_value=common.preview_collections['main']['KISS'].icon_id)

class hair_bunch_add(bpy.types.Operator):
	bl_idname = 'curve.hair_bunch_add'
	bl_label = "髪の房を追加"
	bl_description = "アニメ調の髪の房を追加します"
	bl_options = {'REGISTER', 'UNDO'}
	
	radius = bpy.props.FloatProperty(name="房の半径", default=0.1, min=0, max=10, soft_min=0, soft_max=10, step=10, precision=2)
	random_multi = bpy.props.FloatProperty(name="ランダム要素の強さ", default=0.5, min=0, max=10, soft_min=0, soft_max=10, step=10, precision=2)
	z_plus = bpy.props.FloatProperty(name="中間のZ軸の高さ", default=0.1, min=0, max=10, soft_min=0, soft_max=10, step=10, precision=2)
	
	@classmethod
	def poll(cls, context):
		return True
	
	def invoke(self, context, event):
		import bpy_extras.view3d_utils
		
		self.pre_draw = bpy.types.VIEW3D_HT_header.draw
		def header_draw(self, context):
			row = self.layout.row(align=True)
			row.label(text="ホイール:太さ変更")
			row.label(text="ホイールクリック:ランダム強度変更")
			row.label(text="ZXキー:高さ変更")
		bpy.types.VIEW3D_HT_header.draw = header_draw
		
		if context.active_object:
			if context.active_object.mode != 'OBJECT':
				self.report(type={'ERROR'}, message="オブジェクトモードで実行してください")
				return {'CANCELLED'}
		
		self.end_location = bpy_extras.view3d_utils.region_2d_to_location_3d(context.region, context.region_data, (event.mouse_region_x, event.mouse_region_y), context.space_data.cursor_location)
		
		curve = context.blend_data.curves.new("Hair Bunch", 'CURVE')
		ob = context.blend_data.objects.new("Hair Bunch", curve)
		context.scene.objects.link(ob)
		context.scene.objects.active = ob
		ob.select = True
		
		curve.dimensions = '3D'
		curve.resolution_u = 5
		
		spline = curve.splines.new('NURBS')
		
		spline.points.add(3)
		spline.points[0].radius = 0.0
		spline.points[-1].radius = 0.0
		spline.use_endpoint_u = True
		spline.order_u = 4
		spline.resolution_u = 5
		
		self.set_spline(spline, context)
		
		self.object = ob
		self.curve = curve
		self.spline = spline
		
		bevel_curve = context.blend_data.curves.new("Hair Bunch Bevel", 'CURVE')
		bevel_ob = context.blend_data.objects.new("Hair Bunch Bevel", bevel_curve)
		context.scene.objects.link(bevel_ob)
		bevel_ob.select = True
		curve.bevel_object = bevel_ob
		
		bevel_ob.parent = ob
		bevel_ob.parent_type = 'VERTEX'
		bevel_ob.parent_vertices = (3, 3, 3)
		
		bevel_curve.dimensions = '2D'
		bevel_curve.fill_mode = 'NONE'
		bevel_curve.resolution_u = 2
		
		spline = bevel_curve.splines.new('NURBS')
		spline.points.add(7)
		spline.use_cyclic_u = True
		spline.order_u = 4
		spline.resolution_u = 2
		
		self.bevel_object = bevel_ob
		self.bevel_curve = bevel_curve
		self.bevel_spline = spline
		
		self.set_bevel_spline(spline)
		
		context.window_manager.modal_handler_add(self)
		return {'RUNNING_MODAL'}
	
	def modal(self, context, event):
		import bpy_extras.view3d_utils
		
		#print(event.type, event.value)
		
		if event.type == 'MOUSEMOVE':
			self.end_location = bpy_extras.view3d_utils.region_2d_to_location_3d(context.region, context.region_data, (event.mouse_region_x, event.mouse_region_y), context.space_data.cursor_location)
			self.execute(context)
		
		elif event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
			self.radius += 0.05
			self.set_bevel_spline(self.bevel_spline)
			self.object.update_tag({'OBJECT', 'DATA'})
		elif event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
			self.radius -= 0.05
			self.set_bevel_spline(self.bevel_spline)
			self.object.update_tag({'OBJECT', 'DATA'})
		
		elif event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
			if 0.9 < self.random_multi:
				self.random_multi = 0.0
			elif 0.4 < self.random_multi:
				self.random_multi = 1.0
			else:
				self.random_multi = 0.5
			self.set_bevel_spline(self.bevel_spline)
		
		elif event.type == 'Z' and event.value == 'PRESS':
			self.z_plus += 0.1
			self.execute(context)
		elif event.type == 'X' and event.value == 'PRESS':
			self.z_plus -= 0.1
			self.execute(context)
		
		elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
			bpy.types.VIEW3D_HT_header.draw = self.pre_draw
			context.area.tag_redraw()	
			return {'FINISHED'}
		
		elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
			common.remove_data([self.object, self.bevel_object, self.curve, self.bevel_curve])
			bpy.types.VIEW3D_HT_header.draw = self.pre_draw
			context.area.tag_redraw()
			return {'CANCELLED'}
		
		return {'RUNNING_MODAL'}
	
	def get_random_point(self, co):
		import random
		r = self.radius * self.random_multi
		co.x = co.x + random.uniform(-r, r)
		co.y = co.y + random.uniform(-r, r)
		return co
	
	def set_bevel_spline(self, spline):
		import math, mathutils
		r = self.radius
		vec = mathutils.Vector((0, r, 0))
		min_rad = -math.radians(360 / len(spline.points))
		for index, point in enumerate(spline.points):
			eul = mathutils.Euler((0, 0, min_rad * index), 'XYZ')
			now_vec = vec.copy()
			now_vec.rotate(eul)
			now_vec = self.get_random_point(now_vec)
			point.co = list(now_vec[:]) + [1]
	
	def set_spline(self, spline, context):
		diff_co = self.end_location - context.space_data.cursor_location
		
		plus_co = diff_co * 0.333333
		plus_co.z = -plus_co.z + self.z_plus
		
		point1 = diff_co * 0.333333
		point1 += plus_co * 1
		point1 += context.space_data.cursor_location
		
		point2 = diff_co * 0.666666
		point2 += plus_co * 1
		point2 += context.space_data.cursor_location
		
		spline.points[0].co = list(context.space_data.cursor_location[:]) + [1]
		spline.points[1].co = list(point1[:]) + [1]
		spline.points[2].co = list(point2[:]) + [1]
		spline.points[-1].co = list(self.end_location[:]) + [1]
	
	def execute(self, context):
		try:
			self.set_spline(self.spline, context)
		except:
			self.report(type={'ERROR'}, message="オブジェクトモードで実行してください")
			return {'CANCELLED'}
		return {'FINISHED'}
