import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	icon_id = common.preview_collections['main']['KISS'].icon_id
	self.layout.separator()
	self.layout.operator('object.quick_shape_key_transfer', icon_value=icon_id)
	self.layout.operator('object.precision_shape_key_transfer', icon_value=icon_id)
	self.layout.separator()
	self.layout.operator('object.multiply_shape_key', icon_value=icon_id)
	self.layout.separator()
	self.layout.operator('object.blur_shape_key', icon_value=icon_id)
	self.layout.separator()
	self.layout.operator('object.change_base_shape_key', icon_value=icon_id)

class quick_shape_key_transfer(bpy.types.Operator):
	bl_idname = 'object.quick_shape_key_transfer'
	bl_label = "クイック・シェイプキー転送"
	bl_description = "アクティブなメッシュに他の選択メッシュのシェイプキーを高速で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_first_remove_all = bpy.props.BoolProperty(name="最初に全シェイプキーを削除", default=True)
	subdivide_number = bpy.props.IntProperty(name="参照元の分割", default=1, min=0, max=10, soft_min=0, soft_max=10)
	is_remove_empty = bpy.props.BoolProperty(name="変形のないシェイプキーを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2: return False
		for ob in obs:
			if ob.type != 'MESH':
				return False
			if ob.name != active_ob.name:
				if ob.data.shape_keys:
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_first_remove_all', icon='ERROR')
		self.layout.prop(self, 'subdivide_number', icon='LATTICE_DATA')
		self.layout.prop(self, 'is_remove_empty', icon='X')
	
	def execute(self, context):
		import mathutils, time
		start_time = time.time()
		
		target_ob = context.active_object
		target_me = target_ob.data
		
		pre_mode = target_ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_original_ob = ob
				break
		source_ob = source_original_ob.copy()
		source_me = source_original_ob.data.copy()
		source_ob.data = source_me
		context.scene.objects.link(source_ob)
		context.scene.objects.active = source_ob
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.reveal()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.subdivide(number_cuts=self.subdivide_number, smoothness=0.0, quadtri=False, quadcorner='STRAIGHT_CUT', fractal=0.0, fractal_along_normal=0.0, seed=0)
		source_ob.active_shape_key_index = 0
		bpy.ops.object.mode_set(mode='OBJECT')
		
		if self.is_first_remove_all:
			try:
				target_ob.active_shape_key_index = 1
				bpy.ops.object.shape_key_remove(all=True)
			except:
				pass
		
		kd = mathutils.kdtree.KDTree(len(source_me.vertices))
		for vert in source_me.vertices:
			co = source_ob.matrix_world * vert.co
			kd.insert(co, vert.index)
		kd.balance()
		
		near_vert_indexs = [kd.find(target_ob.matrix_world * v.co)[1] for v in target_me.vertices]
		
		is_shapeds = {}
		relative_keys = []
		context.window_manager.progress_begin(0, len(source_me.shape_keys.key_blocks))
		context.window_manager.progress_update(0)
		for source_shape_key_index, source_shape_key in enumerate(source_me.shape_keys.key_blocks):
			
			if target_me.shape_keys:
				if source_shape_key.name in target_me.shape_keys.key_blocks:
					target_shape_key = target_ob.shape_keys.key_blocks[source_shape_key.name]
				else:
					target_shape_key = target_ob.shape_key_add(name=source_shape_key.name, from_mix=False)
			else:
				target_shape_key = target_ob.shape_key_add(name=source_shape_key.name, from_mix=False)
			
			relative_key_name = source_shape_key.relative_key.name
			if relative_key_name not in relative_keys:
				relative_keys.append(relative_key_name)
			is_shapeds[source_shape_key.name] = False
			
			try:
				target_shape_key.relative_key = target_me.shape_keys.key_blocks[relative_key_name]
			except:
				pass
			
			mat1, mat2 = source_ob.matrix_world, target_ob.matrix_world
			source_shape_keys = [(mat1 * source_shape_key.data[v.index].co * mat2) - (mat1 * source_me.vertices[v.index].co * mat2) for v in source_me.vertices]
			
			for target_vert in target_me.vertices:
				
				near_vert_index = near_vert_indexs[target_vert.index]
				near_shape_co = source_shape_keys[near_vert_index]
				
				target_shape_key.data[target_vert.index].co = target_me.vertices[target_vert.index].co + near_shape_co
				if 0.01 < near_shape_co.length:
					is_shapeds[source_shape_key.name] = True
			
			context.window_manager.progress_update(source_shape_key_index)
		context.window_manager.progress_end()
		
		if self.is_remove_empty:
			for source_shape_key_name, is_shaped in is_shapeds.items():
				if source_shape_key_name not in relative_keys and not is_shaped:
					target_shape_key = target_me.shape_keys.key_blocks[source_shape_key_name]
					target_ob.shape_key_remove(target_shape_key)
		
		target_ob.active_shape_key_index = 0
		
		common.remove_data([source_ob, source_me])
		context.scene.objects.active = target_ob
		bpy.ops.object.mode_set(mode=pre_mode)
		
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		return {'FINISHED'}

class precision_shape_key_transfer(bpy.types.Operator):
	bl_idname = 'object.precision_shape_key_transfer'
	bl_label = "高精度・シェイプキー転送"
	bl_description = "アクティブなメッシュに他の選択メッシュのシェイプキーを高精度で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_first_remove_all = bpy.props.BoolProperty(name="最初に全シェイプキーを削除", default=True)
	subdivide_number = bpy.props.IntProperty(name="参照元の分割", default=1, min=0, max=10, soft_min=0, soft_max=10)
	extend_range = bpy.props.FloatProperty(name="範囲倍率", default=2, min=1.1, max=5, soft_min=1.1, soft_max=5, step=10, precision=2)
	is_remove_empty = bpy.props.BoolProperty(name="変形のないシェイプキーを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2: return False
		for ob in obs:
			if ob.type != 'MESH':
				return False
			if ob.name != active_ob.name:
				if ob.data.shape_keys:
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_first_remove_all', icon='ERROR')
		self.layout.prop(self, 'subdivide_number', icon='LATTICE_DATA')
		self.layout.prop(self, 'extend_range', icon='META_EMPTY')
		self.layout.prop(self, 'is_remove_empty', icon='X')
	
	def execute(self, context):
		import mathutils, time
		start_time = time.time()
		
		target_ob = context.active_object
		target_me = target_ob.data
		
		pre_mode = target_ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_original_ob = ob
				break
		source_ob = source_original_ob.copy()
		source_me = source_original_ob.data.copy()
		source_ob.data = source_me
		context.scene.objects.link(source_ob)
		context.scene.objects.active = source_ob
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.reveal()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.subdivide(number_cuts=self.subdivide_number, smoothness=0.0, quadtri=False, quadcorner='STRAIGHT_CUT', fractal=0.0, fractal_along_normal=0.0, seed=0)
		source_ob.active_shape_key_index = 0
		bpy.ops.object.mode_set(mode='OBJECT')
		
		if self.is_first_remove_all:
			try:
				target_ob.active_shape_key_index = 1
				bpy.ops.object.shape_key_remove(all=True)
			except:
				pass
		
		kd = mathutils.kdtree.KDTree(len(source_me.vertices))
		for vert in source_me.vertices:
			co = source_ob.matrix_world * vert.co
			kd.insert(co, vert.index)
		kd.balance()
		
		context.window_manager.progress_begin(0, len(target_me.vertices))
		progress_reduce = len(target_me.vertices) // 200 + 1
		near_vert_data = []
		near_vert_multi_total = []
		near_vert_multi_total_append = near_vert_multi_total.append
		for vert in target_me.vertices:
			near_vert_data.append([])
			near_vert_data_append = near_vert_data[-1].append
			
			target_co = target_ob.matrix_world * vert.co
			mini_co, mini_index, mini_dist = kd.find(target_co)
			radius = mini_dist * self.extend_range
			diff_radius = radius - mini_dist
			
			multi_total = 0.0
			for co, index, dist in kd.find_range(target_co, radius):
				if 0 < diff_radius:
					multi = (diff_radius - (dist - mini_dist)) / diff_radius
				else:
					multi = 1.0
				near_vert_data_append((index, multi))
				multi_total += multi
			near_vert_multi_total_append(multi_total)
			
			if vert.index % progress_reduce == 0:
				context.window_manager.progress_update(vert.index)
		context.window_manager.progress_end()
		
		is_shapeds = {}
		relative_keys = []
		context.window_manager.progress_begin(0, len(source_me.shape_keys.key_blocks))
		context.window_manager.progress_update(0)
		for source_shape_key_index, source_shape_key in enumerate(source_me.shape_keys.key_blocks):
			
			if target_me.shape_keys:
				if source_shape_key.name in target_me.shape_keys.key_blocks:
					target_shape_key = target_ob.shape_keys.key_blocks[source_shape_key.name]
				else:
					target_shape_key = target_ob.shape_key_add(name=source_shape_key.name, from_mix=False)
			else:
				target_shape_key = target_ob.shape_key_add(name=source_shape_key.name, from_mix=False)
			
			relative_key_name = source_shape_key.relative_key.name
			if relative_key_name not in relative_keys:
				relative_keys.append(relative_key_name)
			is_shapeds[source_shape_key.name] = False
			
			try:
				target_shape_key.relative_key = target_me.shape_keys.key_blocks[relative_key_name]
			except:
				pass
			
			mat1, mat2 = source_ob.matrix_world, target_ob.matrix_world
			source_shape_keys = [(mat1 * source_shape_key.data[v.index].co * mat2) - (mat1 * source_me.vertices[v.index].co * mat2) for v in source_me.vertices]
			
			for target_vert in target_me.vertices:
				
				if 0 < near_vert_multi_total[target_vert.index]:
					
					total_diff_co = mathutils.Vector((0, 0, 0))
					
					for near_index, near_multi in near_vert_data[target_vert.index]:
						total_diff_co += source_shape_keys[near_index] * near_multi
					
					average_diff_co = total_diff_co / near_vert_multi_total[target_vert.index]
				
				else:
					average_diff_co = mathutils.Vector((0, 0, 0))
				
				target_shape_key.data[target_vert.index].co = target_me.vertices[target_vert.index].co + average_diff_co
				if 0.01 < average_diff_co.length:
					is_shapeds[source_shape_key.name] = True
			
			context.window_manager.progress_update(source_shape_key_index)
		context.window_manager.progress_end()
		
		if self.is_remove_empty:
			for source_shape_key_name, is_shaped in is_shapeds.items():
				if source_shape_key_name not in relative_keys and not is_shaped:
					target_shape_key = target_me.shape_keys.key_blocks[source_shape_key_name]
					target_ob.shape_key_remove(target_shape_key)
		
		target_ob.active_shape_key_index = 0
		
		common.remove_data([source_ob, source_me])
		context.scene.objects.active = target_ob
		bpy.ops.object.mode_set(mode=pre_mode)
		
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		return {'FINISHED'}

class multiply_shape_key(bpy.types.Operator):
	bl_idname = 'object.multiply_shape_key'
	bl_label = "シェイプキーの変形に乗算"
	bl_description = "シェイプキーの変形に数値を乗算し、変形の強度を増減させます"
	bl_options = {'REGISTER', 'UNDO'}
	
	multi = bpy.props.FloatProperty(name="倍率", description="シェイプキーの拡大率です", default=1.1, min=-10, max=10, soft_min=-10, soft_max=10, step=10, precision=2)
	items = [
		('ACTIVE', "アクティブのみ", "", 'HAND', 1),
		('UP', "アクティブより上", "", 'TRIA_UP_BAR', 2),
		('DOWN', "アクティブより下", "", 'TRIA_DOWN_BAR', 3),
		('ALL', "全て", "", 'ARROW_LEFTRIGHT', 4),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象", default='ACTIVE')
	
	@classmethod
	def poll(cls, context):
		if context.active_object:
			ob = context.active_object
			if ob.type == 'MESH':
				return ob.active_shape_key
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'multi', icon='ARROW_LEFTRIGHT')
		self.layout.prop(self, 'mode', icon='VIEWZOOM')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		shape_keys = me.shape_keys
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		target_shapes = []
		if self.mode == 'ACTIVE':
			target_shapes.append(ob.active_shape_key)
		elif self.mode == 'UP':
			for index, key_block in enumerate(shape_keys.key_blocks):
				if index <= ob.active_shape_key_index:
					target_shapes.append(key_block)
		elif self.mode == 'UP':
			for index, key_block in enumerate(shape_keys.key_blocks):
				if ob.active_shape_key_index <= index:
					target_shapes.append(key_block)
		elif self.mode == 'ALL':
			for key_block in shape_keys.key_blocks:
				target_shapes.append(key_block)
		
		for shape in target_shapes:
			data = shape.data
			for i, vert in enumerate(me.vertices):
				diff = data[i].co - vert.co
				diff *= self.multi
				data[i].co = vert.co + diff
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}

class blur_shape_key(bpy.types.Operator):
	bl_idname = 'object.blur_shape_key'
	bl_label = "シェイプキーぼかし"
	bl_description = "アクティブ、もしくは全てのシェイプキーをぼかします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 'HAND', 1),
		('UP', "アクティブより上", "", 'TRIA_UP_BAR', 2),
		('DOWN', "アクティブより下", "", 'TRIA_DOWN_BAR', 3),
		('ALL', "全て", "", 'ARROW_LEFTRIGHT', 4),
		]
	target = bpy.props.EnumProperty(items=items, name="対象", default='ACTIVE')
	radius = bpy.props.FloatProperty(name="範囲倍率", default=3, min=0.1, max=50, soft_min=0.1, soft_max=50, step=50, precision=2)
	strength = bpy.props.IntProperty(name="強さ", default=1, min=1, max=10, soft_min=1, soft_max=10)
	items = [
		('BOTH', "増減両方", "", 'AUTOMERGE_ON', 1),
		('ADD', "増加のみ", "", 'TRIA_UP', 2),
		('SUB', "減少のみ", "", 'TRIA_DOWN', 3),
		]
	effect = bpy.props.EnumProperty(items=items, name="ぼかし効果", default='BOTH')
	items = [
		('LINER', "ライナー", "", 'LINCURVE', 1),
		('SMOOTH1', "スムーズ1", "", 'SMOOTHCURVE', 2),
		('SMOOTH2', "スムーズ2", "", 'SMOOTHCURVE', 3),
		]
	blend = bpy.props.EnumProperty(items=items, name="減衰タイプ", default='LINER')
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				return me.shape_keys
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'target', icon='VIEWZOOM')
		self.layout.prop(self, 'radius', icon='META_EMPTY')
		self.layout.prop(self, 'strength', icon='ARROW_LEFTRIGHT')
		self.layout.prop(self, 'effect', icon='BRUSH_BLUR')
		self.layout.prop(self, 'blend', icon='IPO_SINE')
	
	def execute(self, context):
		import bmesh, mathutils
		ob = context.active_object
		me = ob.data
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		bm = bmesh.new()
		bm.from_mesh(me)
		edge_lengths = [e.calc_length() for e in bm.edges]
		bm.free()
		edge_lengths.sort()
		average_edge_length = sum(edge_lengths) / len(edge_lengths)
		center_index = int( (len(edge_lengths) - 1) / 2.0 )
		average_edge_length = (average_edge_length + edge_lengths[center_index]) / 2
		radius = average_edge_length * self.radius
		
		context.window_manager.progress_begin(0, len(me.vertices))
		progress_reduce = len(me.vertices) // 200 + 1
		near_vert_data = []
		kd = mathutils.kdtree.KDTree(len(me.vertices))
		for vert in me.vertices:
			kd.insert(vert.co.copy(), vert.index)
		kd.balance()
		for vert in me.vertices:
			near_vert_data.append([])
			near_vert_data_append = near_vert_data[-1].append
			for co, index, dist in kd.find_range(vert.co, radius):
				multi = (radius - dist) / radius
				if self.blend == 'SMOOTH1':
					multi = common.in_out_quad_blend(multi)
				elif self.blend == 'SMOOTH2':
					multi = common.bezier_blend(multi)
				near_vert_data_append((index, multi))
			if vert.index % progress_reduce == 0:
				context.window_manager.progress_update(vert.index)
		context.window_manager.progress_end()
		
		target_shape_keys = []
		if self.target == 'ACTIVE':
			target_shape_keys.append(ob.active_shape_key)
		elif self.target == 'UP':
			for index, shape_key in enumerate(me.shape_keys.key_blocks):
				if index <= ob.active_shape_key_index:
					target_shape_keys.append(shape_key)
		elif self.target == 'DOWN':
			for index, shape_key in enumerate(me.shape_keys.key_blocks):
				if ob.active_shape_key_index <= index:
					target_shape_keys.append(shape_key)
		elif self.target == 'ALL':
			for index, shape_key in enumerate(me.shape_keys.key_blocks):
				target_shape_keys.append(shape_key)
		
		progress_total = len(target_shape_keys) * self.strength * len(me.vertices)
		context.window_manager.progress_begin(0, progress_total)
		progress_reduce = progress_total // 200 + 1
		progress_count = 0
		for strength_count in range(self.strength):
			for shape_key in target_shape_keys:
				
				shapes = []
				shapes_append = shapes.append
				for index, vert in enumerate(me.vertices):
					co = shape_key.data[index].co - vert.co
					shapes_append(co)
				
				for vert in me.vertices:
					
					target_shape = shapes[vert.index]
					
					total_shape = mathutils.Vector()
					total_multi = 0.0
					for index, multi in near_vert_data[vert.index]:
						co = shapes[index]
						if self.effect == 'ADD':
							if target_shape.length <= co.length:
								total_shape += co * multi
								total_multi += multi
						elif self.effect == 'SUB':
							if co.length <= target_shape.length:
								total_shape += co * multi
								total_multi += multi
						else:
							total_shape += co * multi
							total_multi += multi
					
					if 0 < total_multi:
						average_shape = total_shape / total_multi
					else:
						average_shape = mathutils.Vector()
					
					shape_key.data[vert.index].co = vert.co + average_shape
					
					progress_count += 1
					if progress_count % progress_reduce == 0:
						context.window_manager.progress_update(progress_count)
		
		context.window_manager.progress_end()
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}

class change_base_shape_key(bpy.types.Operator):
	bl_idname = 'object.change_base_shape_key'
	bl_label = "このシェイプキーをベースに"
	bl_description = "アクティブなシェイプキーを他のシェイプキーのベースにします"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_deform_mesh = bpy.props.BoolProperty(name="素メッシュを調整", default=True)
	is_deform_other_shape = bpy.props.BoolProperty(name="他シェイプを調整", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			return ob.type=='MESH' and 1 <= ob.active_shape_key_index
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_deform_mesh', icon='MESH_DATA')
		self.layout.prop(self, 'is_deform_other_shape', icon='SHAPEKEY_DATA')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		target_shape_key = ob.active_shape_key
		old_shape_key = me.shape_keys.key_blocks[0]
		
		for i in range(9**9):
			bpy.ops.object.shape_key_move(type='UP')
			if ob.active_shape_key_index == 0:
				break
		
		target_shape_key.relative_key = target_shape_key
		old_shape_key.relative_key = target_shape_key
		
		if self.is_deform_mesh:
			for vert in me.vertices:
				vert.co = target_shape_key.data[vert.index].co.copy()
		
		if self.is_deform_other_shape:
			for shape_key in me.shape_keys.key_blocks:
				if shape_key.name == target_shape_key.name or shape_key.name == old_shape_key.name:
					continue
				if shape_key.relative_key.name == old_shape_key.name:
					shape_key.relative_key = target_shape_key
					for vert in me.vertices:
						diff_co = target_shape_key.data[vert.index].co - old_shape_key.data[vert.index].co
						shape_key.data[vert.index].co = shape_key.data[vert.index].co + diff_co
		
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}
