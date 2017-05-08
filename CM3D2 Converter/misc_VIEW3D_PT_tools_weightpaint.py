# 「3Dビュー」エリア → 「ウェイトペイント」モード → ツールシェルフ → 「ウェイトツール」パネル
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	icon_id = common.preview_collections['main']['KISS'].icon_id
	box = self.layout.box()
	box.operator('mesh.selected_mesh_vertex_group_blur', text="選択部分をぼかし", icon_value=icon_id)

class selected_mesh_vertex_group_blur(bpy.types.Operator):
	bl_idname = 'mesh.selected_mesh_vertex_group_blur'
	bl_label = "選択部分の頂点グループをぼかす"
	bl_description = "選択メッシュの頂点グループの影響をぼかします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('LINER', "リニア", "", 'LINCURVE', 1),
		('TRIGONOMETRIC', "スムーズ", "", 'SMOOTHCURVE', 2),
		]
	smooth_method = bpy.props.EnumProperty(items=items, name="減衰タイプ", default='TRIGONOMETRIC')
	
	selection_blur_range_multi = bpy.props.FloatProperty(name="選択をぼかす範囲倍率", default=4.0, min=0.0, max=100.0, soft_min=0.0, soft_max=100.0, step=50, precision=1)
	selection_blur_accuracy = bpy.props.IntProperty(name="選択をぼかす分割精度", default=3, min=0, max=10, soft_min=1, soft_max=10)
	
	items = [
		('ALL', "全て", "", 'COLLAPSEMENU', 1),
		('ACTIVE', "アクティブのみ", "", 'LAYER_ACTIVE', 2),
		]
	target_vertex_group = bpy.props.EnumProperty(items=items, name="対象頂点グループ", default='ALL')
	blur_range_multi = bpy.props.FloatProperty(name="ウェイトをぼかす範囲倍率", default=2.0, min=0.0, max=100.0, soft_min=0.0, soft_max=100.0, step=50, precision=1)
	blur_count = bpy.props.IntProperty(name="ウェイトをぼかす回数", default=1, min=1, max=100, soft_min=1, soft_max=100)
	is_vertex_group_limit_total = bpy.props.BoolProperty(name="ウェイト数を4つに制限", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob.type == 'MESH':
			return bool(len(ob.vertex_groups))
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'smooth_method')
		
		self.layout.label(text="選択をぼかす", icon='UV_SYNC_SELECT')
		self.layout.prop(self, 'selection_blur_range_multi', text="範囲 | 辺の長さの平均×")
		self.layout.prop(self, 'selection_blur_accuracy', text="精度 (分割数)")
		
		self.layout.label(text="頂点グループをぼかす", icon='GROUP_VERTEX')
		self.layout.prop(self, 'target_vertex_group', text="対象グループ")
		self.layout.prop(self, 'blur_range_multi', text="範囲 | 辺の長さの平均×")
		self.layout.prop(self, 'blur_count', text="実行回数")
		self.layout.prop(self, 'is_vertex_group_limit_total', icon='IMGDISPLAY')
	
	def execute(self, context):
		class EmptyClass: pass
		
		ob = context.active_object
		me = ob.data
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		pre_selected_objects = context.selected_objects[:]
		for selected_object in pre_selected_objects:
			selected_object.select = False
		ob.select = True
		
		bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
		
		selection_ob = context.active_object
		selection_me = selection_ob.data
		
		for vert in selection_me.vertices:
			if vert.hide:
				vert.hide = False
				vert.select = False
		for edge in selection_me.edges:
			if edge.hide:
				edge.hide = False
				edge.select = False
		for poly in selection_me.polygons:
			if poly.hide:
				poly.hide = False
				poly.select = False
		
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='INVERT')
		if context.tool_settings.mesh_select_mode[0]:
			bpy.ops.mesh.delete(type='VERT')
		elif context.tool_settings.mesh_select_mode[1]:
			bpy.ops.mesh.delete(type='EDGE')
		elif context.tool_settings.mesh_select_mode[2]:
			bpy.ops.mesh.delete(type='FACE')
		bpy.ops.mesh.select_all(action='SELECT')
		if 1 <= self.selection_blur_accuracy:
			bpy.ops.mesh.subdivide(number_cuts=self.selection_blur_accuracy, smoothness=0, quadtri=False, quadcorner='INNERVERT', fractal=0, fractal_along_normal=0, seed=0)
		bpy.ops.object.mode_set(mode='OBJECT')
		
		selection_kd = mathutils.kdtree.KDTree(len(selection_me.vertices))
		for vert in selection_me.vertices:
			selection_kd.insert(vert.co, vert.index)
		selection_kd.balance()
		common.remove_data([selection_ob, selection_me])
		
		ob.select = True
		context.scene.objects.active = ob
		
		bm = bmesh.new()
		bm.from_mesh(me)
		edge_lengths = [e.calc_length() for e in bm.edges]
		bm.free()
		selection_blur_range = edge_lengths[int(len(edge_lengths) * 0.5)] * self.selection_blur_range_multi
		
		vert_selection_values = []
		for vert in me.vertices:
			co, index, dist = selection_kd.find(vert.co)
			if dist <= selection_blur_range + 0.00001:
				if 0 < selection_blur_range:
					if self.smooth_method == 'TRIGONOMETRIC': value = common.trigonometric_smooth(1.0 - (dist / selection_blur_range))
					else: value = 1.0 - (dist / selection_blur_range)
					vert_selection_values.append(value)
				else:
					vert_selection_values.append(1.0)
			else:
				vert_selection_values.append(None)
		
		# 頂点カラーで選択状態を確認
		"""
		preview_vertex_color = me.vertex_colors.new()
		for loop in me.loops:
			v = vert_selection_values[loop.vertex_index]
			if v != None:
				preview_vertex_color.data[loop.index].color = (v, v, v)
			else:
				preview_vertex_color.data[loop.index].color = (0, 0, 0)
		"""
		
		kd = mathutils.kdtree.KDTree(len(me.vertices))
		for vert in me.vertices:
			kd.insert(vert.co, vert.index)
		kd.balance()
		
		blur_range = edge_lengths[int(len(edge_lengths) * 0.5)] * self.blur_range_multi
		
		for i in range(self.blur_count):
			
			pre_weights = []
			for vert in me.vertices:
				pre_vges = []
				for vge in vert.groups:
					pre_vge = EmptyClass()
					pre_vge.vertex_group = ob.vertex_groups[vge.group]
					pre_vge.weight = vge.weight
					if self.target_vertex_group == 'ACTIVE' and ob.vertex_groups.active.name != pre_vge.vertex_group.name: continue
					pre_vges.append(pre_vge)
				pre_weights.append(pre_vges)
			
			new_weights = []
			for vert in me.vertices:
				if vert_selection_values[vert.index] == None:
					new_weights.append([])
					continue
				
				kd_find_ranged = kd.find_range(vert.co, blur_range)
				
				effects = []
				total_effect = 0.0
				for co, index, dist in kd_find_ranged:
					effect = EmptyClass()
					effect.index = index
					if 0 < blur_range:
						if self.smooth_method == 'TRIGONOMETRIC': effect.effect = common.trigonometric_smooth(1.0 - (dist / blur_range))
						else: value = effect.effect = 1.0 - (dist / blur_range)
					else:
						effect.effect = 1.0
					total_effect += effect.effect
					effects.append(effect)
				
				temp_weight_dict = {}
				for effect in effects:
					pre_vges = pre_weights[effect.index]
					for pre_vge in pre_vges:
						if self.target_vertex_group == 'ACTIVE' and ob.vertex_groups.active.name != pre_vge.vertex_group.name: continue
						weight_effect = pre_vge.weight * (effect.effect / total_effect)
						if pre_vge.vertex_group.name in temp_weight_dict:
							temp_weight_dict[pre_vge.vertex_group.name] += weight_effect
						else:
							temp_weight_dict[pre_vge.vertex_group.name] = weight_effect
				
				new_vges = []
				for key, value in temp_weight_dict.items():
					new_vge = EmptyClass()
					new_vge.vertex_group = ob.vertex_groups[key]
					new_vge.weight = value
					if self.target_vertex_group == 'ACTIVE' and ob.vertex_groups.active.name != new_vge.vertex_group.name: continue
					new_vges.append(new_vge)
				new_weights.append(new_vges)
			
			selected_vert_indices = [i for i, v in enumerate(vert_selection_values) if v != None]
			for vg in ob.vertex_groups:
				if self.target_vertex_group == 'ACTIVE' and ob.vertex_groups.active.name != vg.name: continue
				vg.remove(selected_vert_indices)
			
			for index, pre_vges in enumerate(pre_weights):
				if vert_selection_values[index] == None: continue
				for pre_vge in pre_vges:
					if self.target_vertex_group == 'ACTIVE' and ob.vertex_groups.active.name != pre_vge.vertex_group.name: continue
					
					multi = 1.0 - vert_selection_values[index]
					pre_weight = pre_vge.weight * multi
					pre_vge.vertex_group.add([index], pre_weight, 'ADD')
			for index, new_vges in enumerate(new_weights):
				if vert_selection_values[index] == None: continue
				for new_vge in new_vges:
					if self.target_vertex_group == 'ACTIVE' and ob.vertex_groups.active.name != new_vge.vertex_group.name: continue
					
					multi = vert_selection_values[index]
					new_weight = new_vge.weight * multi
					new_vge.vertex_group.add([index], new_weight, 'ADD')
		
		if self.is_vertex_group_limit_total:
			bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
		
		bpy.ops.object.mode_set(mode=pre_mode)
		for selected_object in pre_selected_objects:
			selected_object.select = True
		return {'FINISHED'}
