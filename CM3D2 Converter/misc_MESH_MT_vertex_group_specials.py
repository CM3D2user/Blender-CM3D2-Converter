# 「プロパティ」エリア → 「メッシュデータ」タブ → 「頂点グループ」パネル → ▼ボタン
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	icon_id = common.preview_collections['main']['KISS'].icon_id
	self.layout.separator()
	self.layout.operator('object.quick_transfer_vertex_group', icon_value=icon_id)
	self.layout.operator('object.precision_transfer_vertex_group', icon_value=icon_id)
	self.layout.separator()
	self.layout.operator('object.quick_blur_vertex_group', icon_value=icon_id)
	self.layout.operator('object.blur_vertex_group', icon_value=icon_id)
	self.layout.separator()
	self.layout.operator('object.multiply_vertex_group', icon_value=icon_id)
	self.layout.separator()
	self.layout.operator('object.remove_noassign_vertex_groups', icon_value=icon_id)

class quick_transfer_vertex_group(bpy.types.Operator):
	bl_idname = 'object.quick_transfer_vertex_group'
	bl_label = "クイック・ウェイト転送"
	bl_description = "アクティブなメッシュに他の選択メッシュの頂点グループを高速で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_remove_old_vertex_groups = bpy.props.BoolProperty(name="最初に全頂点グループを削除", default=True)
	items = [
		('NEAREST', "最も近い頂点", "", 'VERTEXSEL', 1),
		('EDGEINTERP_NEAREST', "最も近い辺", "", 'EDGESEL', 2),
		('POLYINTERP_NEAREST', "最も近い面", "", 'FACESEL', 3),
		('POLYINTERP_VNORPROJ', "投影先", "", 'MOD_UVPROJECT', 4),
		]
	vert_mapping = bpy.props.EnumProperty(items=items, name="参照先", default='POLYINTERP_NEAREST')
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2: return False
		for ob in obs:
			if ob.type != 'MESH':
				return False
			if ob.name != active_ob.name:
				if len(ob.vertex_groups):
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_remove_old_vertex_groups', icon='ERROR')
		self.layout.prop(self, 'vert_mapping')
	
	def execute(self, context):
		target_ob = context.active_object
		target_me = target_ob.data
		
		pre_mode = target_ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
				break
		source_me = source_ob.data
		
		if self.is_remove_old_vertex_groups:
			if bpy.ops.object.vertex_group_remove.poll():
				bpy.ops.object.vertex_group_remove(all=True)
		
		bpy.ops.object.data_transfer(use_reverse_transfer=True, use_freeze=False, data_type='VGROUP_WEIGHTS', use_create=True, vert_mapping=self.vert_mapping, use_auto_transform=False, use_object_transform=True, use_max_distance=False, ray_radius=0, layers_select_src='ALL', layers_select_dst='NAME', mix_mode='REPLACE', mix_factor=1)
		
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}

class precision_transfer_vertex_group(bpy.types.Operator):
	bl_idname = 'object.precision_transfer_vertex_group'
	bl_label = "高精度・ウェイト転送"
	bl_description = "アクティブなメッシュに他の選択メッシュの頂点グループを高精度で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_first_remove_all = bpy.props.BoolProperty(name="最初に全頂点グループを削除", default=True)
	subdivide_number = bpy.props.IntProperty(name="参照元の分割", default=1, min=0, max=10, soft_min=0, soft_max=10)
	extend_range = bpy.props.FloatProperty(name="範囲倍率", default=1.5, min=1.1, max=5.0, soft_min=1.1, soft_max=5.0, step=10, precision=2)
	is_remove_empty = bpy.props.BoolProperty(name="割り当てのない頂点グループを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2: return False
		for ob in obs:
			if ob.type != 'MESH':
				return False
			if ob.name != active_ob.name:
				if len(ob.vertex_groups):
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
		bpy.ops.object.mode_set(mode='OBJECT')
		
		if self.is_first_remove_all:
			if bpy.ops.object.vertex_group_remove.poll():
				bpy.ops.object.vertex_group_remove(all=True)
		
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
		
		context.window_manager.progress_begin(0, len(source_ob.vertex_groups))
		for source_vertex_group in source_ob.vertex_groups:
			
			if source_vertex_group.name in target_ob.vertex_groups:
				target_vertex_group = target_ob.vertex_groups[source_vertex_group.name]
			else:
				target_vertex_group = target_ob.vertex_groups.new(source_vertex_group.name)
			
			is_waighted = False
			
			source_weights = []
			source_weights_append = source_weights.append
			for source_vert in source_me.vertices:
				for elem in source_vert.groups:
					if elem.group == source_vertex_group.index:
						source_weights_append(elem.weight)
						break
				else:
					source_weights_append(0.0)
			
			for target_vert in target_me.vertices:
				
				if 0 < near_vert_multi_total[target_vert.index]:
					
					total_weight = [source_weights[i] * m for i, m in near_vert_data[target_vert.index]]
					total_weight = sum(total_weight)
					
					average_weight = total_weight / near_vert_multi_total[target_vert.index]
				else:
					average_weight = 0.0
				
				if 0.000001 < average_weight:
					target_vertex_group.add([target_vert.index], average_weight, 'REPLACE')
					is_waighted = True
				else:
					if not self.is_first_remove_all:
						target_vertex_group.remove([target_vert.index])
				
			context.window_manager.progress_update(source_vertex_group.index)
			
			if not is_waighted and self.is_remove_empty:
				target_ob.vertex_groups.remove(target_vertex_group)
		context.window_manager.progress_end()
		
		target_ob.vertex_groups.active_index = 0
		
		common.remove_data([source_ob, source_me])
		context.scene.objects.active = target_ob
		bpy.ops.object.mode_set(mode=pre_mode)
		
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		return {'FINISHED'}

class quick_blur_vertex_group(bpy.types.Operator):
	bl_idname = 'object.quick_blur_vertex_group'
	bl_label = "頂点グループぼかし"
	bl_description = "アクティブ、もしくは全ての頂点グループをぼかします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 'HAND', 1),
		('ALL', "全て", "", 'ARROW_LEFTRIGHT', 2),
		]
	target = bpy.props.EnumProperty(items=items, name="対象", default='ALL')
	strength = bpy.props.FloatProperty(name="強さ", default=1.0, min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, step=10, precision=3)
	count = bpy.props.IntProperty(name="反復", default=1, min=1, max=256, soft_min=1, soft_max=256)
	size = bpy.props.FloatProperty(name="拡大縮小", default=0.0, min=-1.0, max=1.0, soft_min=-1.0, soft_max=1.0, step=10, precision=3)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return ob.vertex_groups.active
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'target', icon='VIEWZOOM')
		self.layout.prop(self, 'strength')
		self.layout.prop(self, 'count')
		self.layout.prop(self, 'size')
	
	def execute(self, context):
		target_ob = context.active_object
		target_me = target_ob.data
		
		pre_mode = target_ob.mode
		bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
		
		pre_use_paint_mask_vertex = target_me.use_paint_mask_vertex
		target_me.use_paint_mask_vertex = True
		
		bpy.ops.paint.vert_select_all(action='SELECT')
		bpy.ops.object.vertex_group_smooth(group_select_mode=self.target, factor=self.strength, repeat=self.count, expand=self.size, source='ALL')
		
		target_me.use_paint_mask_vertex = pre_use_paint_mask_vertex
		
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}

class blur_vertex_group(bpy.types.Operator):
	bl_idname = 'object.blur_vertex_group'
	bl_label = "旧・頂点グループぼかし"
	bl_description = "アクティブ、もしくは全ての頂点グループをぼかします"
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
	is_normalize = bpy.props.BoolProperty(name="他頂点グループも調節", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return ob.vertex_groups.active
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'target', icon='VIEWZOOM')
		self.layout.prop(self, 'radius', icon='META_EMPTY')
		self.layout.prop(self, 'strength', icon='ARROW_LEFTRIGHT')
		self.layout.prop(self, 'effect', icon='BRUSH_BLUR')
		self.layout.prop(self, 'is_normalize', icon='ALIGN')
	
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
				near_vert_data_append((index, multi))
			if vert.index % progress_reduce == 0:
				context.window_manager.progress_update(vert.index)
		context.window_manager.progress_end()
		
		target_vertex_groups = []
		if self.target == 'ACTIVE':
			target_vertex_groups.append(ob.vertex_groups.active)
		elif self.target == 'UP':
			for vertex_group in ob.vertex_groups:
				if vertex_group.index <= ob.vertex_groups.active_index:
					target_vertex_groups.append(vertex_group)
		elif self.target == 'DOWN':
			for vertex_group in ob.vertex_groups:
				if ob.vertex_groups.active_index <= vertex_group.index:
					target_vertex_groups.append(vertex_group)
		elif self.target == 'ALL':
			for vertex_group in ob.vertex_groups:
				target_vertex_groups.append(vertex_group)
		
		progress_total = len(target_vertex_groups) * self.strength * len(me.vertices)
		context.window_manager.progress_begin(0, progress_total)
		progress_reduce = progress_total // 200 + 1
		progress_count = 0
		for strength_count in range(self.strength):
			for vertex_group in target_vertex_groups:
				
				weights = []
				weights_append = weights.append
				for vert in me.vertices:
					for elem in vert.groups:
						if elem.group == vertex_group.index:
							weights_append(elem.weight)
							break
					else:
						weights_append(0.0)
				
				for vert in me.vertices:
					
					target_weight = weights[vert.index]
					
					total_weight = 0.0
					total_multi = 0.0
					for index, multi in near_vert_data[vert.index]:
						if self.effect == 'ADD':
							if target_weight <= weights[index]:
								total_weight += weights[index] * multi
								total_multi += multi
						elif self.effect == 'SUB':
							if weights[index] <= target_weight:
								total_weight += weights[index] * multi
								total_multi += multi
						else:
							total_weight += weights[index] * multi
							total_multi += multi
					
					if 0 < total_multi:
						average_weight = total_weight / total_multi
					else:
						average_weight = 0.0
					
					if 0.001 < average_weight:
						vertex_group.add([vert.index], average_weight, 'REPLACE')
					else:
						vertex_group.remove([vert.index])
					
					progress_count += 1
					if progress_count % progress_reduce == 0:
						context.window_manager.progress_update(progress_count)
					
					if self.is_normalize:
						
						other_weight_total = 0.0
						for elem in vert.groups:
							if elem.group != vertex_group.index:
								other_weight_total += elem.weight
						
						diff_weight = average_weight - target_weight
						new_other_weight_total = other_weight_total - diff_weight
						if 0 < other_weight_total:
							other_weight_multi = new_other_weight_total / other_weight_total
						else:
							other_weight_multi = 0.0
						
						for elem in vert.groups:
							if elem.group != vertex_group.index:
								vg = ob.vertex_groups[elem.group]
								vg.add([vert.index], elem.weight * other_weight_multi, 'REPLACE')
		
		context.window_manager.progress_end()
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}

class multiply_vertex_group(bpy.types.Operator):
	bl_idname = 'object.multiply_vertex_group'
	bl_label = "頂点グループに乗算"
	bl_description = "頂点グループのウェイトに数値を乗算し、ウェイトの強度を増減させます"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 'HAND', 1),
		('UP', "アクティブより上", "", 'TRIA_UP_BAR', 2),
		('DOWN', "アクティブより下", "", 'TRIA_DOWN_BAR', 3),
		('ALL', "全て", "", 'ARROW_LEFTRIGHT', 4),
		]
	target = bpy.props.EnumProperty(items=items, name="対象", default='ACTIVE')
	value = bpy.props.FloatProperty(name="倍率", default=1.1, min=0.1, max=10, soft_min=0.1, soft_max=10, step=10, precision=2)
	is_normalize = bpy.props.BoolProperty(name="他頂点グループも調節", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return ob.vertex_groups.active
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'target', icon='VIEWZOOM')
		self.layout.prop(self, 'value', icon='ARROW_LEFTRIGHT')
		self.layout.prop(self, 'is_normalize', icon='ALIGN')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		target_vertex_groups = []
		if self.target == 'ACTIVE':
			target_vertex_groups.append(ob.vertex_groups.active)
		elif self.target == 'UP':
			for vertex_group in ob.vertex_groups:
				if vertex_group.index <= ob.vertex_groups.active_index:
					target_vertex_groups.append(vertex_group)
		elif self.target == 'DOWN':
			for vertex_group in ob.vertex_groups:
				if ob.vertex_groups.active_index <= vertex_group.index:
					target_vertex_groups.append(vertex_group)
		elif self.target == 'ALL':
			for vertex_group in ob.vertex_groups:
				target_vertex_groups.append(vertex_group)
		
		for vertex_group in target_vertex_groups:
			for vert in me.vertices:
				
				old_weight = -1
				other_weight_total = 0.0
				for elem in vert.groups:
					if elem.group == vertex_group.index:
						old_weight = elem.weight
					else:
						other_weight_total += elem.weight
				if old_weight == -1:
					continue
				
				new_weight = old_weight * self.value
				vertex_group.add([vert.index], new_weight, 'REPLACE')
				
				if self.is_normalize:
					
					diff_weight = new_weight - old_weight
					
					new_other_weight_total = other_weight_total - diff_weight
					if 0 < other_weight_total:
						other_weight_multi = new_other_weight_total / other_weight_total
					else:
						other_weight_multi = 0.0
					
					for elem in vert.groups:
						if elem.group != vertex_group.index:
							vg = ob.vertex_groups[elem.group]
							vg.add([vert.index], elem.weight * other_weight_multi, 'REPLACE')
		
		bpy.ops.object.mode_set(mode=pre_mode)
		return {'FINISHED'}

class remove_noassign_vertex_groups(bpy.types.Operator):
	bl_idname = 'object.remove_noassign_vertex_groups'
	bl_label = "割り当てのない頂点グループを削除"
	bl_description = "どの頂点にも割り当てられていない頂点グループを全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	threshold = bpy.props.FloatProperty(name="これ以下の影響は切り捨て", default=0.000001, min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, step=1, precision=10)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return bool(len(ob.vertex_groups))
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'threshold')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		is_keeps = [False for i in range(len(ob.vertex_groups))]
		
		for vert in me.vertices:
			for vge in vert.groups:
				if not is_keeps[vge.group]:
					if self.threshold < vge.weight:
						is_keeps[vge.group] = True
		
		copy_vertex_groups = ob.vertex_groups[:]
		for i in range(len(copy_vertex_groups)):
			if not is_keeps[i]:
				ob.vertex_groups.remove(copy_vertex_groups[i])
		
		return {'FINISHED'}
