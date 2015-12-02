import os, re, sys, bpy, bmesh, mathutils, webbrowser, urllib, zipfile, subprocess, urllib.request, datetime, time
from . import common

# アドオンアップデート処理
class update_cm3d2_converter(bpy.types.Operator):
	bl_idname = 'script.update_cm3d2_converter'
	bl_label = "CM3D2 Converterを更新"
	bl_description = "GitHubから最新版のCM3D2 Converterアドオンをダウンロードし上書き更新します"
	bl_options = {'REGISTER'}
	
	is_restart = bpy.props.BoolProperty(name="更新後にBlenderを再起動", default=True)
	is_toggle_console = bpy.props.BoolProperty(name="再起動後にコンソールを閉じる", default=True)
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.menu('INFO_MT_help_CM3D2_Converter_RSS', icon='INFO')
		self.layout.prop(self, 'is_restart', icon='BLENDER')
		self.layout.prop(self, 'is_toggle_console', icon='CONSOLE')
	
	def execute(self, context):
		zip_path = os.path.join(bpy.app.tempdir, "Blender-CM3D2-Converter-master.zip")
		addon_path = os.path.dirname(__file__)
		
		response = urllib.request.urlopen("https://github.com/CM3Duser/Blender-CM3D2-Converter/archive/master.zip")
		zip_file = open(zip_path, "wb")
		zip_file.write(response.read())
		zip_file.close()
		
		zip_file = zipfile.ZipFile(zip_path, "r")
		for path in zip_file.namelist():
			if not os.path.basename(path):
				continue
			sub_dir = os.path.split( os.path.split(path)[0] )[1]
			if sub_dir == "CM3D2 Converter":
				file = open(os.path.join(addon_path, os.path.basename(path)), 'wb')
				file.write(zip_file.read(path))
				file.close()
		zip_file.close()
		
		if self.is_restart:
			filepath = bpy.data.filepath
			command_line = [sys.argv[0]]
			if filepath:
				command_line.append(filepath)
			if self.is_toggle_console:
				py = os.path.join(os.path.dirname(__file__), "console_toggle.py")
				command_line.append('-P')
				command_line.append(py)
			subprocess.Popen(command_line)
			bpy.ops.wm.quit_blender()
		else:
			self.report(type={'INFO'}, message="Blender-CM3D2-Converterを更新しました、再起動して下さい")
		return {'FINISHED'}

class quick_vertex_group_transfer(bpy.types.Operator):
	bl_idname = 'object.quick_vertex_group_transfer'
	bl_label = "クイック・ウェイト転送"
	bl_description = "アクティブなメッシュに他の選択メッシュの頂点グループを高速で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_first_remove_all = bpy.props.BoolProperty(name="最初に全頂点グループを削除", default=True)
	is_remove_empty = bpy.props.BoolProperty(name="割り当てのない頂点グループを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2:
			return False
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
		self.layout.prop(self, 'is_remove_empty', icon='X')
	
	def execute(self, context):
		start_time = time.time()
		
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
				break
		target_me = target_ob.data
		source_me = source_ob.data
		
		pre_mode = target_ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		if self.is_first_remove_all:
			if len(target_ob.vertex_groups):
				bpy.ops.object.vertex_group_remove(all=True)
		
		kd = mathutils.kdtree.KDTree(len(source_me.vertices))
		for vert in source_me.vertices:
			co = source_ob.matrix_world * vert.co
			kd.insert(co, vert.index)
		kd.balance()
		
		near_vert_indexs = []
		for vert in target_me.vertices:
			target_co = target_ob.matrix_world * vert.co
			near_index = kd.find(target_co)[1]
			near_vert_indexs.append(near_index)
		
		context.window_manager.progress_begin(0, len(source_ob.vertex_groups))
		for source_vertex_group in source_ob.vertex_groups:
			
			if source_vertex_group.name in target_ob.vertex_groups.keys():
				target_vertex_group = target_ob.vertex_groups[source_vertex_group.name]
			else:
				target_vertex_group = target_ob.vertex_groups.new(source_vertex_group.name)
			
			is_waighted = False
			
			source_weights = []
			for source_vert in source_me.vertices:
				for elem in source_vert.groups:
					if elem.group == source_vertex_group.index:
						source_weights.append(elem.weight)
						break
				else:
					source_weights.append(0.0)
			
			for target_vert in target_me.vertices:
				
				near_vert_index = near_vert_indexs[target_vert.index]
				near_weight = source_weights[near_vert_index]
				
				if 0.01 < near_weight:
					target_vertex_group.add([target_vert.index], near_weight, 'REPLACE')
					is_waighted = True
				else:
					if not self.is_first_remove_all:
						target_vertex_group.remove([target_vert.index])
			
			context.window_manager.progress_update(source_vertex_group.index)
			
			if not is_waighted and self.is_remove_empty:
				target_ob.vertex_groups.remove(target_vertex_group)
		context.window_manager.progress_end()
		
		target_ob.vertex_groups.active_index = 0
		bpy.ops.object.mode_set(mode=pre_mode)
		
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		return {'FINISHED'}

class precision_vertex_group_transfer(bpy.types.Operator):
	bl_idname = 'object.precision_vertex_group_transfer'
	bl_label = "高精度・ウェイト転送"
	bl_description = "アクティブなメッシュに他の選択メッシュの頂点グループを高精度で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_first_remove_all = bpy.props.BoolProperty(name="最初に全頂点グループを削除", default=True)
	extend_range = bpy.props.FloatProperty(name="範囲倍率", default=2, min=1.1, max=5, soft_min=1.1, soft_max=5, step=10, precision=2)
	is_remove_empty = bpy.props.BoolProperty(name="割り当てのない頂点グループを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2:
			return False
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
		self.layout.prop(self, 'extend_range', icon='META_EMPTY')
		self.layout.prop(self, 'is_remove_empty', icon='X')
	
	def execute(self, context):
		start_time = time.time()
		
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
				break
		target_me = target_ob.data
		source_me = source_ob.data
		
		pre_mode = target_ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		if self.is_first_remove_all:
			if len(target_ob.vertex_groups):
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
		for vert in target_me.vertices:
			near_vert_data.append([])
			
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
				near_vert_data[-1].append((index, multi))
				multi_total += multi
			near_vert_multi_total.append(multi_total)
			
			if vert.index % progress_reduce == 0:
				context.window_manager.progress_update(vert.index)
		context.window_manager.progress_end()
		
		context.window_manager.progress_begin(0, len(source_ob.vertex_groups))
		for source_vertex_group in source_ob.vertex_groups:
			
			if source_vertex_group.name in target_ob.vertex_groups.keys():
				target_vertex_group = target_ob.vertex_groups[source_vertex_group.name]
			else:
				target_vertex_group = target_ob.vertex_groups.new(source_vertex_group.name)
			
			is_waighted = False
			
			source_weights = []
			for source_vert in source_me.vertices:
				for elem in source_vert.groups:
					if elem.group == source_vertex_group.index:
						source_weights.append(elem.weight)
						break
				else:
					source_weights.append(0.0)
			
			for target_vert in target_me.vertices:
				
				if 0 < near_vert_multi_total[target_vert.index]:
					
					total_weight = 0.0
					
					for near_index, near_multi in near_vert_data[target_vert.index]:
						total_weight += source_weights[near_index] * near_multi
					
					average_weight = total_weight / near_vert_multi_total[target_vert.index]
				else:
					average_weight = 0.0
				
				if 0.01 < average_weight:
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
		bpy.ops.object.mode_set(mode=pre_mode)
		
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		return {'FINISHED'}

class blur_vertex_group(bpy.types.Operator):
	bl_idname = 'object.blur_vertex_group'
	bl_label = "頂点グループぼかし"
	bl_description = "アクティブ、もしくは全ての頂点グループをぼかします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象ウェイト", default='ACTIVE')
	radius = bpy.props.IntProperty(name="範囲:辺×", default=1, min=1, max=10, soft_min=1, soft_max=10, step=1)
	blur_count = bpy.props.IntProperty(name="処理回数", default=10, min=1, max=100, soft_min=1, soft_max=100, step=1)
	items = [
		('BOTH', "増減両方", "", 1),
		('ADD', "増加のみ", "", 2),
		('SUB', "減少のみ", "", 3),
		]
	effect = bpy.props.EnumProperty(items=items, name="ぼかし効果", default='BOTH')
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return bool(ob.vertex_groups.active)
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'mode', icon='ACTION')
		#self.layout.prop(self, 'radius', icon='UV_EDGESEL')
		self.layout.prop(self, 'blur_count', icon='BRUSH_BLUR')
		self.layout.prop(self, 'effect', icon='BRUSH_ADD')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		target_vertex_groups = []
		if self.mode == 'ACTIVE':
			target_vertex_groups.append(ob.vertex_groups.active)
		else:
			for vertex_group in ob.vertex_groups:
				target_vertex_groups.append(vertex_group)
		
		bm = bmesh.new()
		bm.from_mesh(me)
		bm.verts.ensure_lookup_table()
		near_vert_data = []
		for vert in bm.verts:
			near_vert_data.append([])
			near_vert_data[-1].append( (vert.index, None) )
			near_vert_indexs = [vert.index]
			for radius_count in range(self.radius):
				for near_vert_index, near_vert_multi in near_vert_data[-1][:]:
					for edge in bm.verts[near_vert_index].link_edges:
						for edge_vert in edge.verts:
							if edge_vert.index not in near_vert_indexs:
								multi = (self.radius - radius_count) / self.radius
								near_vert_data[-1].append( (edge_vert.index, multi) )
								near_vert_indexs.append(edge_vert.index)
								break
			del near_vert_data[-1][0]
		
		context.window_manager.progress_begin(0, self.blur_count * len(target_vertex_groups) * len(bm.verts))
		progress_count = 0
		
		for blur_count_index in range(self.blur_count):
			for vertex_group in target_vertex_groups:
				new_vert_weights = []
				for vert in bm.verts:
					context.window_manager.progress_update(progress_count)
					progress_count += 1
					
					try:
						target_vert_weight = vertex_group.weight(vert.index)
					except:
						target_vert_weight = 0.0
					
					near_weight_average = 0.0
					near_weight_total = 0.0
					for near_vert_index, near_vert_multi in near_vert_data[vert.index]:
						try:
							near_vert_weight = vertex_group.weight(near_vert_index)
						except:
							near_vert_weight = 0.0
						
						if self.effect == 'ADD':
							if target_vert_weight < near_vert_weight:
								near_weight_average += near_vert_weight
								near_weight_total += 1
						elif self.effect == 'SUB':
							if near_vert_weight < target_vert_weight:
								near_weight_average += near_vert_weight
								near_weight_total += 1
						else:
							near_weight_average += near_vert_weight
							near_weight_total += 1
					
					if 0.0 < near_weight_total:
						near_weight_average /= near_weight_total
						new_vert_weights.append( ((target_vert_weight * 2) + near_weight_average) / 3 )
					else:
						new_vert_weights.append(target_vert_weight)
				
				for vert_index, new_weight in enumerate(new_vert_weights):
					if new_weight <= 0.001:
						vertex_group.remove([vert_index])
					else:
						vertex_group.add([vert_index], new_weight, 'REPLACE')
		
		bm.free()
		bpy.ops.object.mode_set(mode=pre_mode)
		context.window_manager.progress_end()
		return {'FINISHED'}

class multiply_vertex_group(bpy.types.Operator):
	bl_idname = 'object.multiply_vertex_group'
	bl_label = "頂点グループを拡大/縮小"
	bl_description = "頂点グループに数値を掛け算して、影響を増減させます"
	bl_options = {'REGISTER', 'UNDO'}
	
	value = bpy.props.FloatProperty(name="掛ける数", default=1.1, min=0.1, max=10, soft_min=0.1, soft_max=10, step=10, precision=2)
	is_normalize = bpy.props.BoolProperty(name="他頂点グループも調節", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				return bool(ob.vertex_groups.active)
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'value', icon='X')
		self.layout.prop(self, 'is_normalize', icon='ALIGN')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		vertex_group = ob.vertex_groups.active
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
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

class radius_blur_vertex_group(bpy.types.Operator):
	bl_idname = 'object.radius_blur_vertex_group'
	bl_label = "頂点グループ範囲ぼかし"
	bl_description = "アクティブ、もしくは全ての頂点グループを一定の範囲でぼかします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象頂点グループ", default='ACTIVE')
	radius_multi = bpy.props.FloatProperty(name="範囲：辺の長さの平均×", default=2, min=0.1, max=10, soft_min=0.1, soft_max=10, step=10, precision=1)
	blur_count = bpy.props.IntProperty(name="処理回数", default=5, min=1, max=100, soft_min=1, soft_max=100, step=1)
	use_clean = bpy.props.BoolProperty(name="ウェイト0.0は頂点グループから除外", default=True)
	fadeout = bpy.props.BoolProperty(name="距離で影響減退", default=False)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				if ob.vertex_groups.active:
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'mode')
		self.layout.prop(self, 'radius_multi')
		self.layout.prop(self, 'blur_count')
		self.layout.prop(self, 'use_clean')
		self.layout.prop(self, 'fadeout')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		bm = bmesh.new()
		bm.from_mesh(me)
		total_len = 0.0
		for edge in bm.edges:
			total_len += edge.calc_length()
		radius = (total_len / len(bm.edges)) * self.radius_multi
		bm.free()
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		target_weights = []
		if (self.mode == 'ACTIVE'):
			target_weights.append(ob.vertex_groups.active)
		elif (self.mode == 'ALL'):
			for vg in ob.vertex_groups:
				target_weights.append(vg)
		kd = mathutils.kdtree.KDTree(len(me.vertices))
		for i, v in enumerate(me.vertices):
			kd.insert(v.co, i)
		kd.balance()
		context.window_manager.progress_begin(0, self.blur_count * len(target_weights) * len(me.vertices))
		total_count = 0
		for count in range(self.blur_count):
			for vg in target_weights:
				new_weights = []
				for vert in me.vertices:
					total_count += 1
					context.window_manager.progress_update(total_count)
					for group in vert.groups:
						if group.group == vg.index:
							active_weight = group.weight
							break
					else:
						active_weight = 0.0
					near_weights = []
					near_weights_len = []
					for co, index, dist in kd.find_range(vert.co, radius):
						if index != vert.index:
							if self.fadeout:
								vec = co - vert.co
								near_weights_len.append(radius - vec.length)
							for group in me.vertices[index].groups:
								if group.group == vg.index:
									near_weights.append(group.weight)
									break
							else:
								near_weights.append(0.0)
					near_weight_average = 0.0
					near_weights_total = 0
					for weight_index, weight in enumerate(near_weights):
						if not self.fadeout:
							near_weight_average += weight
							near_weights_total += 1
						else:
							multi = near_weights_len[weight_index] / radius
							near_weight_average += weight * multi
							near_weights_total += multi
					try:
						near_weight_average /= near_weights_total
					except ZeroDivisionError:
						near_weight_average = 0.0
					new_weights.append( (active_weight*2 + near_weight_average) / 3 )
				for vert, weight in zip(me.vertices, new_weights):
					if (self.use_clean and weight <= 0.000001):
						vg.remove([vert.index])
					else:
						vg.add([vert.index], weight, 'REPLACE')
		bpy.ops.object.mode_set(mode=pre_mode)
		context.window_manager.progress_end()
		return {'FINISHED'}

class convert_cm3d2_vertex_group_names(bpy.types.Operator):
	bl_idname = "object.convert_cm3d2_vertex_group_names"
	bl_label = "頂点グループ名をCM3D2用→Blender用に変換"
	bl_description = "CM3D2で使われてるボーン名(頂点グループ名)をBlenderで左右対称編集できるように変換します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				if ob.vertex_groups.active:
					for vg in ob.vertex_groups:
						if re.search(r'[_ ]([rRlL])[_ ]', vg.name):
							return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		convert_count = 0
		context.window_manager.progress_begin(0, len(ob.vertex_groups))
		for vg_index, vg in enumerate(ob.vertex_groups[:]):
			context.window_manager.progress_update(vg_index)
			vg_name = common.decode_bone_name(vg.name)
			if vg_name != vg.name:
				if vg_name in ob.vertex_groups.keys():
					target_vg = ob.vertex_groups[vg_name]
					for vert in me.vertices:
						try:
							weight = vg.weight(vert.index)
						except:
							weight = 0.0
						try:
							target_weight = target_vg.weight(vert.index)
						except:
							target_weight = 0.0
						if 0.0 < weight + target_weight:
							target_vg.add([vert.index], weight + target_weight, 'REPLACE')
					ob.vertex_groups.remove(vg)
				else:
					vg.name = vg_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="頂点グループ名をBlender用に変換しました")
		context.window_manager.progress_end()
		return {'FINISHED'}

class convert_cm3d2_vertex_group_names_restore(bpy.types.Operator):
	bl_idname = "object.convert_cm3d2_vertex_group_names_restore"
	bl_label = "頂点グループ名をBlender用→CM3D2用に変換"
	bl_description = "CM3D2で使われてるボーン名(頂点グループ名)に戻します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				if ob.vertex_groups.active:
					for vg in ob.vertex_groups:
						if vg.name.count('*') == 1:
							if re.search(r'\.([rRlL])$', vg.name):
								return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		convert_count = 0
		context.window_manager.progress_begin(0, len(ob.vertex_groups))
		for vg_index, vg in enumerate(ob.vertex_groups[:]):
			context.window_manager.progress_update(vg_index)
			vg_name = common.encode_bone_name(vg.name)
			if vg_name != vg.name:
				if vg_name in ob.vertex_groups.keys():
					target_vg = ob.vertex_groups[vg_name]
					for vert in me.vertices:
						try:
							weight = vg.weight(vert.index)
						except:
							weight = 0.0
						try:
							target_weight = target_vg.weight(vert.index)
						except:
							target_weight = 0.0
						if 0.0 < weight + target_weight:
							target_vg.add([vert.index], weight + target_weight, 'REPLACE')
					ob.vertex_groups.remove(vg)
				else:
					vg.name = vg_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="頂点グループ名をCM3D2用に戻しました")
		context.window_manager.progress_end()
		return {'FINISHED'}

class quick_shape_key_transfer(bpy.types.Operator):
	bl_idname = 'object.quick_shape_key_transfer'
	bl_label = "クイック・シェイプキー転送"
	bl_description = "アクティブなメッシュに他の選択メッシュのシェイプキーを高速で転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_first_remove_all = bpy.props.BoolProperty(name="最初に全シェイプキーを削除", default=True)
	is_remove_empty = bpy.props.BoolProperty(name="変形のないシェイプキーを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2:
			return False
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
		self.layout.prop(self, 'is_remove_empty', icon='X')
	
	def execute(self, context):
		start_time = time.time()
		
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
				break
		target_me = target_ob.data
		source_me = source_ob.data
		
		pre_mode = target_ob.mode
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
		
		near_vert_indexs = []
		for vert in target_me.vertices:
			target_co = target_ob.matrix_world * vert.co
			near_index = kd.find(target_co)[1]
			near_vert_indexs.append(near_index)
		
		is_shapeds = {}
		relative_keys = []
		context.window_manager.progress_begin(0, len(source_me.shape_keys.key_blocks))
		context.window_manager.progress_update(0)
		for source_shape_key_index, source_shape_key in enumerate(source_me.shape_keys.key_blocks):
			
			if target_me.shape_keys:
				if source_shape_key.name in target_me.shape_keys.key_blocks.keys():
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
			
			source_shape_keys = []
			for source_vert in source_me.vertices:
				shape_key_co = source_ob.matrix_world * source_shape_key.data[source_vert.index].co * target_ob.matrix_world
				vert_co = source_ob.matrix_world * source_me.vertices[source_vert.index].co * target_ob.matrix_world
				source_shape_keys.append(shape_key_co - vert_co)
			
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
	extend_range = bpy.props.FloatProperty(name="範囲倍率", default=2, min=1.1, max=5, soft_min=1.1, soft_max=5, step=10, precision=2)
	is_remove_empty = bpy.props.BoolProperty(name="変形のないシェイプキーを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		active_ob = context.active_object
		obs = context.selected_objects
		if len(obs) != 2:
			return False
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
		self.layout.prop(self, 'extend_range', icon='META_EMPTY')
		self.layout.prop(self, 'is_remove_empty', icon='X')
	
	def execute(self, context):
		start_time = time.time()
		
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
				break
		target_me = target_ob.data
		source_me = source_ob.data
		
		pre_mode = target_ob.mode
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
		for vert in target_me.vertices:
			near_vert_data.append([])
			
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
				near_vert_data[-1].append((index, multi))
				multi_total += multi
			near_vert_multi_total.append(multi_total)
			
			if vert.index % progress_reduce == 0:
				context.window_manager.progress_update(vert.index)
		context.window_manager.progress_end()
		
		is_shapeds = {}
		relative_keys = []
		context.window_manager.progress_begin(0, len(source_me.shape_keys.key_blocks))
		context.window_manager.progress_update(0)
		for source_shape_key_index, source_shape_key in enumerate(source_me.shape_keys.key_blocks):
			
			if target_me.shape_keys:
				if source_shape_key.name in target_me.shape_keys.key_blocks.keys():
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
			
			source_shape_keys = []
			for source_vert in source_me.vertices:
				shape_key_co = source_ob.matrix_world * source_shape_key.data[source_vert.index].co * target_ob.matrix_world
				vert_co = source_ob.matrix_world * source_me.vertices[source_vert.index].co * target_ob.matrix_world
				source_shape_keys.append(shape_key_co - vert_co)
			
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
		bpy.ops.object.mode_set(mode=pre_mode)
		
		diff_time = time.time() - start_time
		self.report(type={'INFO'}, message=str(round(diff_time, 1)) + " Seconds")
		return {'FINISHED'}

class scale_shape_key(bpy.types.Operator):
	bl_idname = 'object.scale_shape_key'
	bl_label = "シェイプキーの変形を拡大/縮小"
	bl_description = "シェイプキーの変形を強力にしたり、もしくは弱くできます"
	bl_options = {'REGISTER', 'UNDO'}
	
	multi = bpy.props.FloatProperty(name="倍率", description="シェイプキーの拡大率です", default=1.1, min=-10, max=10, soft_min=-10, soft_max=10, step=10, precision=2)
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象シェイプキー", default='ACTIVE')
	
	@classmethod
	def poll(cls, context):
		if context.active_object:
			ob = context.active_object
			if ob.type == 'MESH':
				if ob.active_shape_key:
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'multi')
		self.layout.prop(self, 'mode')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		shape_keys = me.shape_keys
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		if self.mode == 'ACTIVE':
			target_shapes = [ob.active_shape_key]
		elif self.mode == 'ALL':
			target_shapes = []
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
	bl_description = "シェイプキーの変形をぼかしてスムーズにします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象シェイプキー", default='ACTIVE')
	strength = bpy.props.IntProperty(name="処理回数", description="ぼかしの強度(回数)を設定します", default=5, min=1, max=100, soft_min=1, soft_max=100, step=1)
	items = [
		('BOTH', "増減両方", "", 1),
		('ADD', "増加のみ", "", 2),
		('SUB', "減少のみ", "", 3),
		]
	effect = bpy.props.EnumProperty(items=items, name="ぼかし効果", default='BOTH')
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			return ob.type=='MESH' and ob.active_shape_key
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'mode')
		self.layout.prop(self, 'strength')
		self.layout.prop(self, 'effect')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		shape_keys = me.shape_keys
		
		bm = bmesh.new()
		bm.from_mesh(me)
		
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		if self.mode == 'ACTIVE':
			target_shapes = [ob.active_shape_key]
		elif self.mode == 'ALL':
			target_shapes = []
			for key_block in shape_keys.key_blocks:
				target_shapes.append(key_block)
		context.window_manager.progress_begin(0, len(bm.verts) * len(target_shapes) * self.strength)
		
		near_vert_index = []
		for vert_index, vert in enumerate(bm.verts):
			near_vert_index.append([])
			for edge in vert.link_edges:
				for v in edge.verts:
					if vert_index != v.index:
						near_vert_index[-1].append(v.index)
		
		total_count = 0
		for strength_count in range(self.strength):
			for shape in target_shapes:
				data = shape.data
				new_co = []
				for vert_index, vert in enumerate(bm.verts):
					context.window_manager.progress_update(total_count)
					total_count += 1
					
					source_diff_co = data[vert_index].co - vert.co
					
					average_co = mathutils.Vector((0, 0, 0))
					average_total = 0
					for index in near_vert_index[vert_index]:
						diff_co = data[index].co - me.vertices[index].co
						
						if self.effect == 'ADD':
							if source_diff_co.length < diff_co.length:
								average_co += diff_co
								average_total += 1
						elif self.effect == 'SUB':
							if diff_co.length < source_diff_co.length:
								average_co += diff_co
								average_total += 1
						else:
							average_co += diff_co
							average_total += 1
					
					if 0 < average_total:
						average_co /= average_total
						new_co.append(((source_diff_co * 2) + average_co) / 3 + vert.co)
					else:
						new_co.append(source_diff_co + vert.co)
				for i, co in enumerate(new_co):
					data[i].co = co.copy()
		
		bpy.ops.object.mode_set(mode=pre_mode)
		context.window_manager.progress_end()
		return {'FINISHED'}

class radius_blur_shape_key(bpy.types.Operator):
	bl_idname = 'object.radius_blur_shape_key'
	bl_label = "シェイプキー範囲ぼかし"
	bl_description = "シェイプキーの変形を一定範囲の頂点でぼかしてスムーズにします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象シェイプキー", default='ACTIVE')
	blur_count = bpy.props.IntProperty(name="処理回数", default=1, min=1, max=100, soft_min=1, soft_max=100, step=1)
	items = [
		('BOTH', "増減両方", "", 1),
		('ADD', "増加のみ", "", 2),
		('SUB', "減少のみ", "", 3),
		]
	effect = bpy.props.EnumProperty(items=items, name="ぼかし効果", default='BOTH')
	radius_multi = bpy.props.FloatProperty(name="範囲：辺の長さの平均×", default=2, min=0.1, max=10, soft_min=0.1, soft_max=10, step=100, precision=1)
	is_shaped_radius = bpy.props.BoolProperty(name="モーフ変形後の範囲", default=False)
	fadeout = bpy.props.BoolProperty(name="距離で影響減退", default=True)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			return ob.type=='MESH' and ob.active_shape_key
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'mode')
		self.layout.prop(self, 'blur_count')
		self.layout.prop(self, 'effect')
		self.layout.prop(self, 'radius_multi')
		self.layout.prop(self, 'is_shaped_radius')
		self.layout.prop(self, 'fadeout')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		bm = bmesh.new()
		bm.from_mesh(me)
		total_len = 0.0
		for edge in bm.edges:
			total_len += edge.calc_length()
		radius = (total_len / len(bm.edges)) * self.radius_multi
		bm.free()
		
		shape_keys = me.shape_keys
		pre_mode = ob.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		if self.mode == 'ACTIVE':
			target_shapes = [ob.active_shape_key]
		elif self.mode == 'ALL':
			target_shapes = []
			for key_block in shape_keys.key_blocks:
				target_shapes.append(key_block)
		
		if not self.is_shaped_radius:
			kd = mathutils.kdtree.KDTree(len(me.vertices))
			for i, v in enumerate(me.vertices):
				kd.insert(v.co, i)
			kd.balance()
			
			near_verts = []
			for vert in me.vertices:
				near_verts.append([])
				for co, index, dist in kd.find_range(vert.co, radius):
					diff = vert.co - co
					multi = (radius - diff.length) / radius
					near_verts[-1].append((index, multi))
		
		context.window_manager.progress_begin(0, self.blur_count * len(target_shapes) * len(me.vertices))
		total_count = 0
		for count in range(self.blur_count):
			for shape in target_shapes:
				data = shape.data
				
				if self.is_shaped_radius:
					kd = mathutils.kdtree.KDTree(len(me.vertices))
					for i, v in enumerate(data):
						kd.insert(v.co, i)
					kd.balance()
					near_verts = []
				
				new_co = []
				for vert in me.vertices:
					context.window_manager.progress_update(total_count)
					total_count += 1
					
					if self.is_shaped_radius:
						near_verts.append([])
						for co, index, dist in kd.find_range(data[vert.index].co, radius):
							diff = data[vert.index].co - co
							multi = (radius - diff.length) / radius
							near_verts[-1].append((index, multi))
					
					source_diff_co = data[vert.index].co - vert.co
					
					average_co = mathutils.Vector((0, 0, 0))
					nears_total = 0
					for index, multi in near_verts[vert.index]:
						diff_co = data[index].co - me.vertices[index].co
						if self.fadeout:
							if self.effect == 'ADD':
								if source_diff_co.length < diff_co.length:
									average_co += diff_co * multi
									nears_total += multi
							elif self.effect == 'SUB':
								if diff_co.length < source_diff_co.length:
									average_co += diff_co * multi
									nears_total += multi
							else:
								average_co += diff_co * multi
								nears_total += multi
						else:
							if self.effect == 'ADD':
								if source_diff_co.length < diff_co.length:
									average_co += diff_co
									nears_total += 1
							elif self.effect == 'SUB':
								if diff_co.length < source_diff_co.length:
									average_co += diff_co
									nears_total += 1
							else:
								average_co += diff_co
								nears_total += 1
					
					if 0 < nears_total:
						average_co /= nears_total
						new_co.append(((source_diff_co * 2) + average_co) / 3 + vert.co)
					else:
						new_co.append(source_diff_co + vert.co)
				for i, co in enumerate(new_co):
					data[i].co = co.copy()
		bpy.ops.object.mode_set(mode=pre_mode)
		context.window_manager.progress_end()
		return {'FINISHED'}

class new_cm3d2(bpy.types.Operator):
	bl_idname = 'material.new_cm3d2'
	bl_label = "CM3D2用マテリアルを新規作成"
	bl_description = "Blender-CM3D2-Converterで使用できるマテリアルを新規で作成します"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('CM3D2/Toony_Lighted', "トゥーン", "", 0),
		('CM3D2/Toony_Lighted_Hair', "トゥーン 髪", "", 1),
		('CM3D2/Toony_Lighted_Trans', "トゥーン 透過", "", 2),
		('CM3D2/Toony_Lighted_Trans_NoZ', "トゥーン 透過 NoZ", "", 3),
		('CM3D2/Toony_Lighted_Outline', "トゥーン 輪郭線", "", 4),
		('CM3D2/Toony_Lighted_Hair_Outline', "トゥーン 輪郭線 髪", "", 5),
		('CM3D2/Toony_Lighted_Outline_Trans', "トゥーン 輪郭線 透過", "", 6),
		('CM3D2/Lighted_Trans', "透過", "", 7),
		('Unlit/Texture', "発光", "", 8),
		('Unlit/Transparent', "発光 透過", "", 9),
		('CM3D2/Mosaic', "モザイク", "", 10),
		('CM3D2/Man', "ご主人様", "", 11),
		('Diffuse', "リアル", "", 12),
		]
	type = bpy.props.EnumProperty(items=items, name="種類", default='CM3D2/Toony_Lighted_Outline')
	is_decorate = bpy.props.BoolProperty(name="種類に合わせてマテリアルを装飾", default=True)
	is_replace_cm3d2_tex = bpy.props.BoolProperty(name="テクスチャを探す", default=False, description="CM3D2本体のインストールフォルダからtexファイルを探して開きます")
	
	@classmethod
	def poll(cls, context):
		if 'material' in dir(context):
			if not context.material:
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		if not re.search(r'^[^\.]+\.[^\.]+$', common.remove_serial_number(context.active_object.name)):
			self.layout.label(text="オブジェクト名を設定してからの作成を推奨", icon='CANCEL')
		self.layout.separator()
		self.layout.prop(self, 'type', icon='ANTIALIASED')
		self.layout.prop(self, 'is_decorate', icon='TEXTURE_SHADED')
		self.layout.prop(self, 'is_replace_cm3d2_tex', icon='BORDERMOVE')
	
	def execute(self, context):
		ob = context.active_object
		ob_names = common.remove_serial_number(ob.name).split('.')
		if not context.material_slot:
			bpy.ops.object.material_slot_add()
		mate = context.blend_data.materials.new(ob_names[0])
		context.material_slot.material = mate
		tex_list, col_list, f_list = [], [], []
		
		ob_name = ob_names[0]
		
		base_path = "Assets\\texture\\texture\\"
		
		_MainTex = base_path + ob_name + ".png"
		toonGrayA1 = base_path + r"toon\toonGrayA1.png"
		_ShadowTex = base_path + ob_name + "_shadow.png"
		toonDress_shadow = base_path + r"toon\toonDress_shadow.png"
		
		if False:
			pass
		elif self.type == 'CM3D2/Toony_Lighted_Outline':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Outline'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_OutlineColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_OutlineWidth", 0.002))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'CM3D2/Toony_Lighted_Trans':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Trans'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Trans'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'CM3D2/Toony_Lighted_Hair_Outline':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Hair_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Hair_Outline'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			tex_list.append(("_HiTex", ob_name + "_s", base_path + ob_name + "_s.png"))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_OutlineColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_OutlineWidth", 0.002))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
			f_list.append(("_HiRate", 0.5))
			f_list.append(("_HiPow", 0.001))
		elif self.type == 'CM3D2/Mosaic':
			mate['shader1'] = 'CM3D2/Mosaic'
			mate['shader2'] = 'CM3D2__Mosaic'
			tex_list.append(("_RenderTex", ""))
			f_list.append(("_FloatValue1", 30))
		elif self.type == 'Unlit/Texture':
			mate['shader1'] = 'Unlit/Texture'
			mate['shader2'] = 'Unlit__Texture'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			col_list.append(("_Color", (1, 1, 1, 1)))
		elif self.type == 'Unlit/Transparent':
			mate['shader1'] = 'Unlit/Transparent'
			mate['shader2'] = 'Unlit__Transparent'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 1))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'CM3D2/Man':
			mate['shader1'] = 'CM3D2/Man'
			mate['shader2'] = 'CM3D2__Man'
			col_list.append(("_Color", (1, 1, 1, 1)))
			f_list.append(("_FloatValue2", 0.5))
			f_list.append(("_FloatValue3", 1))
		elif self.type == 'Diffuse':
			mate['shader1'] = 'Diffuse'
			mate['shader2'] = 'Diffuse'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			col_list.append(("_Color", (1, 1, 1, 1)))
		elif self.type == 'CM3D2/Toony_Lighted_Trans_NoZ':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Trans_NoZ'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Trans_NoZ'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_OutlineColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_OutlineWidth", 0.002))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'CM3D2/Toony_Lighted_Outline_Trans':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Outline_Trans'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Outline_Trans'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_OutlineColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_OutlineWidth", 0.002))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'CM3D2/Lighted_Trans':
			mate['shader1'] = 'CM3D2/Lighted_Trans'
			mate['shader2'] = 'CM3D2__Lighted_Trans'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
		elif self.type == 'CM3D2/Toony_Lighted':
			mate['shader1'] = 'CM3D2/Toony_Lighted'
			mate['shader2'] = 'CM3D2__Toony_Lighted'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'CM3D2/Toony_Lighted_Hair':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Hair_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Hair_Outline'
			tex_list.append(("_MainTex", ob_name, _MainTex))
			tex_list.append(("_ToonRamp", "toonGrayA1", toonGrayA1))
			tex_list.append(("_ShadowTex", ob_name + "_shadow", _ShadowTex))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", toonDress_shadow))
			tex_list.append(("_HiTex", ob_name + "_s", base_path + ob_name + "_s.png"))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
			f_list.append(("_HiRate", 0.5))
			f_list.append(("_HiPow", 0.001))
		
		slot_count = 0
		for data in tex_list:
			slot = mate.texture_slots.create(slot_count)
			tex = context.blend_data.textures.new(data[0], 'IMAGE')
			slot.texture = tex
			if data[1] == "":
				slot_count += 1
				continue
			slot.color = [0, 0, 1]
			img = context.blend_data.images.new(data[1], 128, 128)
			img.filepath = data[2]
			img['cm3d2_path'] = data[2]
			img.source = 'FILE'
			tex.image = img
			slot_count += 1
			
			# tex探し
			if self.is_replace_cm3d2_tex:
				if common.replace_cm3d2_tex(img) and data[0]=='_MainTex':
					me = ob.data
					for face in me.polygons:
						if face.material_index == ob.active_material_index:
							me.uv_textures.active.data[face.index].image = img
		
		for data in col_list:
			slot = mate.texture_slots.create(slot_count)
			mate.use_textures[slot_count] = False
			slot.color = data[1][:3]
			slot.diffuse_color_factor = data[1][3]
			slot.use_rgb_to_intensity = True
			tex = context.blend_data.textures.new(data[0], 'IMAGE')
			slot.texture = tex
			slot_count += 1
		
		for data in f_list:
			slot = mate.texture_slots.create(slot_count)
			mate.use_textures[slot_count] = False
			slot.diffuse_color_factor = data[1]
			tex = context.blend_data.textures.new(data[0], 'IMAGE')
			slot.texture = tex
			slot_count += 1
		
		common.decorate_material(mate, self.is_decorate)
		return {'FINISHED'}

class copy_material(bpy.types.Operator):
	bl_idname = 'material.copy_material'
	bl_label = "マテリアルをクリップボードにコピー"
	bl_description = "表示しているマテリアルをテキスト形式でクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'material' in dir(context):
			mate = context.material
			if mate:
				if 'shader1' in mate.keys() and 'shader2' in mate.keys():
					return True
		return False
	
	def execute(self, context):
		mate = context.material
		
		output_text = "1000" + "\n"
		output_text = output_text + mate.name.lower() + "\n"
		output_text = output_text + mate.name + "\n"
		output_text = output_text + mate['shader1'] + "\n"
		output_text = output_text + mate['shader2'] + "\n"
		output_text = output_text + "\n"
		
		for tex_slot in mate.texture_slots:
			if not tex_slot:
				continue
			tex = tex_slot.texture
			if tex_slot.use:
				type = 'tex'
			else:
				if tex_slot.use_rgb_to_intensity:
					type = 'col'
				else:
					type = 'f'
			output_text = output_text + type + "\n"
			output_text = output_text + "\t" + common.remove_serial_number(tex.name) + "\n"
			if type == 'tex':
				try:
					img = tex.image
				except:
					self.report(type={'ERROR'}, message="texタイプの設定値の取得に失敗しました、中止します")
					return {'CANCELLED'}
				if img:
					output_text = output_text + '\ttex2d' + "\n"
					output_text = output_text + "\t" + common.remove_serial_number(img.name) + "\n"
					if 'cm3d2_path' in img.keys():
						path = img['cm3d2_path']
					else:
						path = img.filepath
					path = path.replace('\\', '/')
					path = re.sub(r'^[\/\.]*', "", path)
					if not re.search(r'^assets/texture/', path, re.I):
						path = "Assets/texture/texture/" + os.path.basename(path)
					output_text = output_text + "\t" + path + "\n"
					col = tex_slot.color
					output_text = output_text + "\t" + " ".join([str(col[0]), str(col[1]), str(col[2]), str(tex_slot.diffuse_color_factor)]) + "\n"
				else:
					output_text = output_text + "\tnull" + "\n"
			elif type == 'col':
				col = tex_slot.color
				output_text = output_text + "\t" + " ".join([str(col[0]), str(col[1]), str(col[2]), str(tex_slot.diffuse_color_factor)]) + "\n"
			elif type == 'f':
				output_text = output_text + "\t" + str(tex_slot.diffuse_color_factor) + "\n"
		
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="マテリアルテキストをクリップボードにコピーしました")
		return {'FINISHED'}

class paste_material(bpy.types.Operator):
	bl_idname = "material.paste_material"
	bl_label = "クリップボードからマテリアルを貼り付け"
	bl_description = "クリップボード内のマテリアル情報から新規マテリアルを作成します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_decorate = bpy.props.BoolProperty(name="種類に合わせてマテリアルを装飾", default=True)
	
	@classmethod
	def poll(cls, context):
		data = context.window_manager.clipboard
		lines = data.split('\n')
		if len(lines) < 10:
			return False
		match_strs = ['\ntex\n', '\ncol\n', '\nf\n', '\n\t_MainTex\n', '\n\t_Color\n', '\n\t_Shininess\n']
		for s in match_strs:
			if s in data:
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_decorate')
	
	def execute(self, context):
		data = context.window_manager.clipboard
		lines = data.split('\n')
		
		if not context.material_slot:
			bpy.ops.object.material_slot_add()
		mate = context.blend_data.materials.new(lines[2])
		context.material_slot.material = mate
		
		mate['shader1'] = lines[3]
		mate['shader2'] = lines[4]
		
		slot_index = 0
		line_seek = 5
		for i in range(99999):
			if len(lines) <= line_seek:
				break
			type = common.line_trim(lines[line_seek])
			if not type:
				line_seek += 1
				continue
			if type == 'tex':
				slot = mate.texture_slots.create(slot_index)
				tex = context.blend_data.textures.new(common.line_trim(lines[line_seek+1]), 'IMAGE')
				slot.texture = tex
				sub_type = common.line_trim(lines[line_seek+2])
				line_seek += 3
				if sub_type == 'tex2d':
					img = context.blend_data.images.new(common.line_trim(lines[line_seek]), 128, 128)
					img['cm3d2_path'] = common.line_trim(lines[line_seek+1])
					img.filepath = img['cm3d2_path']
					img.source = 'FILE'
					tex.image = img
					fs = common.line_trim(lines[line_seek+2]).split(' ')
					for fi in range(len(fs)):
						fs[fi] = float(fs[fi])
					slot.color = fs[:3]
					slot.diffuse_color_factor = fs[3]
					line_seek += 3
			
			elif type == 'col':
				slot = mate.texture_slots.create(slot_index)
				tex_name = common.line_trim(lines[line_seek+1])
				tex = context.blend_data.textures.new(tex_name, 'IMAGE')
				mate.use_textures[slot_index] = False
				slot.use_rgb_to_intensity = True
				fs = common.line_trim(lines[line_seek+2]).split(' ')
				for fi in range(len(fs)):
					fs[fi] = float(fs[fi])
				slot.color = fs[:3]
				slot.diffuse_color_factor = fs[3]
				slot.texture = tex
				line_seek += 3
			
			elif type == 'f':
				slot = mate.texture_slots.create(slot_index)
				tex_name = common.line_trim(lines[line_seek+1])
				tex = context.blend_data.textures.new(tex_name, 'IMAGE')
				mate.use_textures[slot_index] = False
				slot.diffuse_color_factor = float(common.line_trim(lines[line_seek+2]))
				slot.texture = tex
				line_seek += 3
			
			else:
				self.report(type={'ERROR'}, message="未知の設定値タイプが見つかりました、中止します")
				return {'CANCELLED'}
			slot_index += 1
		
		common.decorate_material(mate, self.is_decorate)
		self.report(type={'INFO'}, message="クリップボードからマテリアルを貼り付けました")
		return {'FINISHED'}

class convert_cm3d2_bone_names(bpy.types.Operator):
	bl_idname = "armature.convert_cm3d2_bone_names"
	bl_label = "ボーン名をCM3D2用→Blender用に変換"
	bl_description = "CM3D2で使われてるボーン名をBlenderで左右対称編集できるように変換します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				for bone in arm.bones:
					if re.search(r'[_ ]([rRlL])[_ ]', bone.name):
						return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		arm = ob.data
		convert_count = 0
		for bone in arm.bones:
			bone_name = common.decode_bone_name(bone.name)
			if bone_name != bone.name:
				bone.name = bone_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="ボーン名をBlender用に変換しました")
		return {'FINISHED'}

class convert_cm3d2_bone_names_restore(bpy.types.Operator):
	bl_idname = "armature.convert_cm3d2_bone_names_restore"
	bl_label = "ボーン名をBlender用→CM3D2用に変換"
	bl_description = "CM3D2で使われてるボーン名に元に戻します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				for bone in arm.bones:
					if bone.name.count('*') == 1:
						if re.search(r'\.([rRlL])$', bone.name):
							return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		arm = ob.data
		convert_count = 0
		for bone in arm.bones:
			bone_name = common.encode_bone_name(bone.name)
			if bone_name != bone.name:
				bone.name = bone_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="ボーン名をCM3D2用に戻しました")
		return {'FINISHED'}

class show_text(bpy.types.Operator):
	bl_idname = "text.show_text"
	bl_label = "テキストを表示"
	bl_description = "指定したテキストをこの領域に表示します"
	bl_options = {'REGISTER', 'UNDO'}
	
	name = bpy.props.StringProperty(name="テキスト名")
	
	@classmethod
	def poll(cls, context):
		if 'text' in dir(context.space_data):
			return True
		return False
	
	def execute(self, context):
		context.space_data.text = bpy.data.texts[self.name]
		return {'FINISHED'}

class copy_text_bone_data(bpy.types.Operator):
	bl_idname = "text.copy_text_bone_data"
	bl_label = "テキストのボーン情報をコピー"
	bl_description = "テキストのボーン情報をカスタムプロパティへ貼り付ける形にしてクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'BoneData' in context.blend_data.texts.keys():
			if 'LocalBoneData' in context.blend_data.texts.keys():
				return True
		return False
	
	def execute(self, context):
		output_text = ""
		for line in context.blend_data.texts['BoneData'].as_string().split('\n'):
			if not line:
				continue
			output_text = output_text + "BoneData:" + line + "\n"
		for line in context.blend_data.texts['LocalBoneData'].as_string().split('\n'):
			if not line:
				continue
			output_text = output_text + "LocalBoneData:" + line + "\n"
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="ボーン情報をクリップボードにコピーしました")
		return {'FINISHED'}

class paste_text_bone_data(bpy.types.Operator):
	bl_idname = "text.paste_text_bone_data"
	bl_label = "テキストのボーン情報を貼り付け"
	bl_description = "クリップボード内のボーン情報をテキストデータに貼り付けます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		clipboard = context.window_manager.clipboard
		if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
			return True
		return False
	
	def execute(self, context):
		clipboard = context.window_manager.clipboard
		if "BoneData" in context.blend_data.texts.keys():
			bone_data_text = context.blend_data.texts["BoneData"]
			bone_data_text.clear()
		else:
			bone_data_text = context.blend_data.texts.new("BoneData")
		if "LocalBoneData" in context.blend_data.texts.keys():
			local_bone_data_text = context.blend_data.texts["LocalBoneData"]
			local_bone_data_text.clear()
		else:
			local_bone_data_text = context.blend_data.texts.new("LocalBoneData")
		
		for line in context.window_manager.clipboard.split("\n"):
			r = re.search('^BoneData:(.+)$', line)
			if r:
				if line.count(',') == 4:
					info = r.groups()[0]
					bone_data_text.write(info + "\n")
			r = re.search('^LocalBoneData:(.+)$', line)
			if r:
				if line.count(',') == 1:
					info = r.groups()[0]
					local_bone_data_text.write(info + "\n")
		bone_data_text.current_line_index = 0
		local_bone_data_text.current_line_index = 0
		self.report(type={'INFO'}, message="ボーン情報をクリップボードから貼り付けました")
		return {'FINISHED'}

class remove_all_material_texts(bpy.types.Operator):
	bl_idname = "text.remove_all_material_texts"
	bl_label = "マテリアル情報テキストを全削除"
	bl_description = "CM3D2で使用できるマテリアルテキストを全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_keep_used_material = bpy.props.BoolProperty(name="使用する分は保管", default=True)
	
	@classmethod
	def poll(cls, context):
		if 'Material:0' in context.blend_data.texts.keys():
			return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_keep_used_material')
	
	def execute(self, context):
		remove_texts = []
		pass_count = 0
		for i in range(9999):
			name = 'Material:' + str(i)
			if name in context.blend_data.texts.keys():
				remove_texts.append(context.blend_data.texts[name])
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		if self.is_keep_used_material:
			ob = context.active_object
			if ob:
				remove_texts = remove_texts[len(ob.material_slots):]
		for txt in remove_texts:
			context.blend_data.texts.remove(txt)
		return {'FINISHED'}

class copy_object_bone_data_property(bpy.types.Operator):
	bl_idname = "object.copy_object_bone_data_property"
	bl_label = "ボーン情報をコピー"
	bl_description = "カスタムプロパティのボーン情報をクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if 'BoneData:0' in ob.keys() and 'LocalBoneData:0' in ob.keys():
				return True
		return False
	
	def execute(self, context):
		output_text = ""
		ob = context.active_object
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob.keys():
				output_text = output_text + "BoneData:" + ob[name] + "\n"
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob.keys():
				output_text = output_text + "LocalBoneData:" + ob[name] + "\n"
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="ボーン情報をクリップボードにコピーしました")
		return {'FINISHED'}

class paste_object_bone_data_property(bpy.types.Operator):
	bl_idname = "object.paste_object_bone_data_property"
	bl_label = "ボーン情報を貼り付け"
	bl_description = "カスタムプロパティのボーン情報をクリップボードから貼り付けます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			clipboard = context.window_manager.clipboard
			if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
				return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		bone_data_count = 0
		local_bone_data_count = 0
		for line in context.window_manager.clipboard.split("\n"):
			r = re.search('^BoneData:(.+)$', line)
			if r:
				if line.count(',') == 4:
					info = r.groups()[0]
					name = "BoneData:" + str(bone_data_count)
					ob[name] = info
					bone_data_count += 1
			r = re.search('^LocalBoneData:(.+)$', line)
			if r:
				if line.count(',') == 1:
					info = r.groups()[0]
					name = "LocalBoneData:" + str(local_bone_data_count)
					ob[name] = info
					local_bone_data_count += 1
		self.report(type={'INFO'}, message="ボーン情報をクリップボードから貼り付けました")
		return {'FINISHED'}

class remove_object_bone_data_property(bpy.types.Operator):
	bl_idname = "object.remove_object_bone_data_property"
	bl_label = "ボーン情報を削除"
	bl_description = "カスタムプロパティのボーン情報を全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if 'BoneData:0' in ob.keys() and 'LocalBoneData:0' in ob.keys():
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="カスタムプロパティのボーン情報を全て削除します", icon='CANCEL')
	
	def execute(self, context):
		ob = context.active_object
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		self.report(type={'INFO'}, message="ボーン情報を削除しました")
		return {'FINISHED'}

class copy_armature_bone_data_property(bpy.types.Operator):
	bl_idname = "object.copy_armature_bone_data_property"
	bl_label = "ボーン情報をコピー"
	bl_description = "カスタムプロパティのボーン情報をクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				if 'BoneData:0' in arm.keys() and 'LocalBoneData:0' in arm.keys():
					return True
		return False
	
	def execute(self, context):
		output_text = ""
		ob = context.active_object.data
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob.keys():
				output_text = output_text + "BoneData:" + ob[name] + "\n"
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob.keys():
				output_text = output_text + "LocalBoneData:" + ob[name] + "\n"
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="ボーン情報をクリップボードにコピーしました")
		return {'FINISHED'}

class paste_armature_bone_data_property(bpy.types.Operator):
	bl_idname = "object.paste_armature_bone_data_property"
	bl_label = "ボーン情報を貼り付け"
	bl_description = "カスタムプロパティのボーン情報をクリップボードから貼り付けます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				clipboard = context.window_manager.clipboard
				if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
					return True
		return False
	
	def execute(self, context):
		ob = context.active_object.data
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		bone_data_count = 0
		local_bone_data_count = 0
		for line in context.window_manager.clipboard.split("\n"):
			r = re.search('^BoneData:(.+)$', line)
			if r:
				if line.count(',') == 4:
					info = r.groups()[0]
					name = "BoneData:" + str(bone_data_count)
					ob[name] = info
					bone_data_count += 1
			r = re.search('^LocalBoneData:(.+)$', line)
			if r:
				if line.count(',') == 1:
					info = r.groups()[0]
					name = "LocalBoneData:" + str(local_bone_data_count)
					ob[name] = info
					local_bone_data_count += 1
		self.report(type={'INFO'}, message="ボーン情報をクリップボードから貼り付けました")
		return {'FINISHED'}

class remove_armature_bone_data_property(bpy.types.Operator):
	bl_idname = "object.remove_armature_bone_data_property"
	bl_label = "ボーン情報を削除"
	bl_description = "カスタムプロパティのボーン情報を全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				if 'BoneData:0' in arm.keys() and 'LocalBoneData:0' in arm.keys():
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="カスタムプロパティのボーン情報を全て削除します", icon='CANCEL')
	
	def execute(self, context):
		ob = context.active_object.data
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob.keys():
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		self.report(type={'INFO'}, message="ボーン情報を削除しました")
		return {'FINISHED'}

class open_url(bpy.types.Operator):
	bl_idname = "wm.open_url"
	bl_label = "URLを開く"
	bl_description = "URLをブラウザで開きます"
	bl_options = {'REGISTER', 'UNDO'}
	
	url = bpy.props.StringProperty(name="URL")
	
	def execute(self, context):
		webbrowser.open(self.url)
		return {'FINISHED'}

class show_image(bpy.types.Operator):
	bl_idname = "image.show_image"
	bl_label = "画像を表示"
	bl_description = "指定の画像をUV/画像エディターに表示します"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	
	def execute(self, context):
		if self.image_name in context.blend_data.images.keys():
			img = context.blend_data.images[self.image_name]
		else:
			self.report(type={'ERROR'}, message="指定された画像が見つかりません")
			return {'CANCELLED'}
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			for space in area.spaces:
				if space.type == 'IMAGE_EDITOR':
					space.image = img
		else:
			self.report(type={'ERROR'}, message="画像を表示できるエリアが見つかりませんでした")
			return {'CANCELLED'}
		return {'FINISHED'}

class show_cm3d2_converter_preference(bpy.types.Operator):
	bl_idname = "wm.show_cm3d2_converter_preference"
	bl_label = "CM3D2 Converterの設定画面を開く"
	bl_description = "CM3D2 Converterアドオンの設定画面を表示します"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		import addon_utils
		my_info = None
		for module in addon_utils.modules():
			info = addon_utils.module_bl_info(module)
			if info['name'] == "CM3D2 Converter":
				my_info = info
				break
		area = common.get_request_area(context, 'USER_PREFERENCES')
		if area and my_info:
			context.user_preferences.active_section = 'ADDONS'
			context.window_manager.addon_search = my_info['name']
			context.window_manager.addon_filter = 'All'
			if 'COMMUNITY' not in context.window_manager.addon_support:
				context.window_manager.addon_support = {'OFFICIAL', 'COMMUNITY'}
			if not my_info['show_expanded']:
				bpy.ops.wm.addon_expand(module=my_info['name'])
		else:
			self.report(type={'ERROR'}, message="表示できるエリアが見つかりませんでした")
			return {'CANCELLED'}
		return {'FINISHED'}

class sync_tex_color_ramps(bpy.types.Operator):
	bl_idname = "texture.sync_tex_color_ramps"
	bl_label = "設定をテクスチャの色に同期"
	bl_description = "この設定値をテクスチャの色に適用してわかりやすくします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'texture_slot' in dir(context):
			if context.texture_slot:
				if 'texture' in dir(context):
					if context.texture:
						return True
		return False
	
	def execute(self, context):
		for mate in context.blend_data.materials:
			if 'shader1' in mate.keys() and 'shader2' in mate.keys():
				for slot in mate.texture_slots:
					if not slot:
						continue
					common.set_texture_color(slot)
		return {'FINISHED'}

class replace_cm3d2_tex(bpy.types.Operator):
	bl_idname = "image.replace_cm3d2_tex"
	bl_label = "テクスチャを探す"
	bl_description = "CM3D2本体のインストールフォルダからtexファイルを探して開きます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'texture' in dir(context):
			tex = context.texture
			if 'image' in dir(tex):
				return True
		return False
	
	def execute(self, context):
		tex = context.texture
		img = tex.image
		if not common.replace_cm3d2_tex(img):
			self.report(type={'ERROR'}, message="見つかりませんでした")
			return {'CANCELLED'}
		return {'FINISHED'}



# 頂点グループメニューに項目追加
def MESH_MT_vertex_group_specials(self, context):
	self.layout.separator()
	self.layout.operator('object.quick_vertex_group_transfer', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator('object.precision_vertex_group_transfer', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator('object.multiply_vertex_group', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator(blur_vertex_group.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator(radius_blur_vertex_group.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator(convert_cm3d2_vertex_group_names.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id, text="頂点グループ名を CM3D2 → Blender")
	self.layout.operator(convert_cm3d2_vertex_group_names_restore.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id, text="頂点グループ名を Blender → CM3D2")

# シェイプメニューに項目追加
def MESH_MT_shape_key_specials(self, context):
	self.layout.separator()
	self.layout.operator('object.quick_shape_key_transfer', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator('object.precision_shape_key_transfer', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator(scale_shape_key.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator(blur_shape_key.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator(radius_blur_shape_key.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)

# マテリアルタブに項目追加
def MATERIAL_PT_context_material(self, context):
	mate = context.material
	if not mate:
		col = self.layout.column(align=True)
		col.operator(new_cm3d2.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
		row = col.row(align=True)
		row.operator('material.import_cm3d2_mate', icon='FILE_FOLDER', text="mateから")
		row.operator(paste_material.bl_idname, icon='PASTEDOWN', text="クリップボードから")
	else:
		if 'shader1' in mate.keys() and 'shader2' in mate.keys():
			box = self.layout.box()
			#row = box.split(percentage=0.3)
			row = box.row()
			row.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			row.operator('material.export_cm3d2_mate', icon='FILE_FOLDER', text="")
			row.operator(copy_material.bl_idname, icon='COPYDOWN', text="")
			
			type_name = "不明"
			if mate['shader1'] == 'CM3D2/Toony_Lighted':
				type_name = "トゥーン"
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Hair':
				type_name = "トゥーン 髪"
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Trans':
				type_name = "トゥーン 透過"
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Trans_NoZ':
				type_name = "トゥーン 透過 NoZ"
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Outline':
				type_name = "トゥーン 輪郭線"
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Hair_Outline':
				type_name = "トゥーン 輪郭線 髪"
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Outline_Trans':
				type_name = "トゥーン 輪郭線 透過"
			elif mate['shader1'] == 'CM3D2/Lighted_Trans':
				type_name = "透過"
			elif mate['shader1'] == 'Unlit/Texture':
				type_name = "発光"
			elif mate['shader1'] == 'Unlit/Transparent':
				type_name = "発光 透過"
			elif mate['shader1'] == 'CM3D2/Mosaic':
				type_name = "モザイク"
			elif mate['shader1'] == 'CM3D2/Man':
				type_name = "ご主人様"
			elif mate['shader1'] == 'Diffuse':
				type_name = "リアル"
			
			row = box.split(percentage=0.3)
			row.label(text="種類:", icon='ANTIALIASED')
			row.label(text=type_name)
			box.prop(mate, 'name', icon='SORTALPHA', text="マテリアル名")
			box.prop(mate, '["shader1"]', icon='MATERIAL', text="シェーダー1")
			box.prop(mate, '["shader2"]', icon='SMOOTH', text="シェーダー2")

# アーマチュアタブに項目追加
def DATA_PT_context_arm(self, context):
	ob = context.active_object
	if ob:
		if ob.type == 'ARMATURE':
			arm = ob.data
			
			flag = False
			for bone in arm.bones:
				if not flag and re.search(r'[_ ]([rRlL])[_ ]', bone.name):
					flag = True
				if not flag and bone.name.count('*') == 1:
					if re.search(r'\.([rRlL])$', bone.name):
						flag = True
				if flag:
					col = self.layout.column(align=True)
					col.label(text="CM3D2用 ボーン名変換", icon_value=common.preview_collections['main']['KISS'].icon_id)
					row = col.row(align=True)
					row.operator(convert_cm3d2_bone_names.bl_idname, text="CM3D2 → Blender", icon='BLENDER')
					row.operator(convert_cm3d2_bone_names_restore.bl_idname, text="Blender → CM3D2", icon='POSE_DATA')
					break
			
			bone_data_count = 0
			if 'BoneData:0' in arm.keys() and 'LocalBoneData:0' in arm.keys():
				for key in arm.keys():
					if re.search(r'^(Local)?BoneData:\d+$', key):
						bone_data_count += 1
			enabled_clipboard = False
			clipboard = context.window_manager.clipboard
			if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
				enabled_clipboard = True
			
			if bone_data_count or enabled_clipboard:
				col = self.layout.column(align=True)
				row = col.row(align=True)
				row.label(text="CM3D2用ボーン情報", icon_value=common.preview_collections['main']['KISS'].icon_id)
				sub_row = row.row()
				sub_row.alignment = 'RIGHT'
				if bone_data_count:
					sub_row.label(text=str(bone_data_count), icon='CHECKBOX_HLT')
				else:
					sub_row.label(text="0", icon='CHECKBOX_DEHLT')
				row = col.row(align=True)
				row.operator(copy_armature_bone_data_property.bl_idname, icon='COPYDOWN', text="コピー")
				row.operator(paste_armature_bone_data_property.bl_idname, icon='PASTEDOWN', text="貼り付け")
				row.operator(remove_armature_bone_data_property.bl_idname, icon='X', text="")

# オブジェクトタブに項目追加
def OBJECT_PT_context_object(self, context):
	ob = context.active_object
	if ob:
		if ob.type == 'MESH':
			if re.search(r'^[^\.]+\.[^\.]+$', ob.name):
				name, base = ob.name.split('.')
				row = self.layout.row(align=True)
				sub_row = row.row()
				sub_row.label(text="model名:", icon='SORTALPHA')
				sub_row.label(text=name)
				sub_row = row.row()
				sub_row.label(text="基点ボーン名:", icon='CONSTRAINT_BONE')
				sub_row.label(text=base)
			else:
				#row.label(text="CM3D2には使えないオブジェクト名です", icon='ERROR')
				pass
			
			bone_data_count = 0
			if 'BoneData:0' in ob.keys() and 'LocalBoneData:0' in ob.keys():
				for key in ob.keys():
					if re.search(r'^(Local)?BoneData:\d+$', key):
						bone_data_count += 1
			enabled_clipboard = False
			clipboard = context.window_manager.clipboard
			if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
				enabled_clipboard = True
			
			if bone_data_count or enabled_clipboard:
				col = self.layout.column(align=True)
				row = col.row(align=True)
				row.label(text="CM3D2用ボーン情報", icon_value=common.preview_collections['main']['KISS'].icon_id)
				sub_row = row.row()
				sub_row.alignment = 'RIGHT'
				if 'BoneData:0' in ob.keys() and 'LocalBoneData:0' in ob.keys():
					bone_data_count = 0
					for key in ob.keys():
						if re.search(r'^(Local)?BoneData:\d+$', key):
							bone_data_count += 1
					sub_row.label(text=str(bone_data_count), icon='CHECKBOX_HLT')
				else:
					sub_row.label(text="0", icon='CHECKBOX_DEHLT')
				row = col.row(align=True)
				row.operator(copy_object_bone_data_property.bl_idname, icon='COPYDOWN', text="コピー")
				row.operator(paste_object_bone_data_property.bl_idname, icon='PASTEDOWN', text="貼り付け")
				row.operator(remove_object_bone_data_property.bl_idname, icon='X', text="")

# モディファイアタブに項目追加
def DATA_PT_modifiers(self, context):
	if 'apply_all_modifier' not in dir(bpy.ops.object):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if me.shape_keys and len(ob.modifiers):
					self.layout.operator(open_url.bl_idname, text="モディファイアを適用できない場合", icon_value=common.preview_collections['main']['KISS'].icon_id).url = "https://sites.google.com/site/matosus304blendernotes/home/download#apply_modifier"

# テキストヘッダーに項目追加
def TEXT_HT_header(self, context):
	texts = bpy.data.texts
	text_keys = texts.keys()
	self.layout.label(text="CM3D2用:", icon_value=common.preview_collections['main']['KISS'].icon_id)
	row = self.layout.row(align=True)
	if 'BoneData' in text_keys:
		txt = bpy.data.texts['BoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator(show_text.bl_idname, icon='ARMATURE_DATA', text="BoneData (%d)" % line_count).name = 'BoneData'
	if 'LocalBoneData' in text_keys:
		txt = bpy.data.texts['LocalBoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator(show_text.bl_idname, icon='BONE_DATA', text="LocalBoneData (%d)" % line_count).name = 'LocalBoneData'
	if 'BoneData' in text_keys and 'LocalBoneData' in text_keys:
		row.operator(copy_text_bone_data.bl_idname, icon='COPYDOWN', text="")
		row.operator(paste_text_bone_data.bl_idname, icon='PASTEDOWN', text="")
	if 'Material:0' in text_keys:
		self.layout.label(text="", icon='MATERIAL_DATA')
		row = self.layout.row(align=True)
		pass_count = 0
		for i in range(99):
			name = "Material:" + str(i)
			if name in text_keys:
				sub_row = row.row(align=True)
				sub_row.scale_x = 0.5
				sub_row.operator(show_text.bl_idname, text=str(i)).name = name
			else:
				pass_count += 1
			if 9 < pass_count:
				break
		if "Material:0" in text_keys:
			row.operator(remove_all_material_texts.bl_idname, icon='X', text="")

# UV/画像エディターのプロパティに項目追加
def IMAGE_PT_image_properties(self, context):
	if 'edit_image' in dir(context):
		img = context.edit_image
		if 'cm3d2_path' in img.keys():
			box = self.layout.box()
			box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			box.prop(img, '["cm3d2_path"]', icon='ANIM_DATA', text="内部パス")

# UV/画像エディターのヘッダーに項目追加
def IMAGE_HT_header(self, context):
	if 'edit_image' in dir(context):
		img = context.edit_image
		if 'cm3d2_path' in img.keys():
			self.layout.label(text="CM3D2用: 内部パス", icon_value=common.preview_collections['main']['KISS'].icon_id)
			row = self.layout.row()
			row.prop(img, '["cm3d2_path"]', text="")
			row.scale_x = 3.0

# テクスチャタブに項目追加
def TEXTURE_PT_context_texture(self, context):
	try:
		tex_slot = context.texture_slot
		tex = context.texture
		mate = context.active_object.active_material
		mate['shader1']
		mate['shader2']
	except:
		return
	if not tex_slot:
		return
	if tex_slot.use:
		type = "tex"
	else:
		if tex_slot.use_rgb_to_intensity:
			type = "col"
		else:
			type = "f"
	
	box = self.layout.box()
	box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
	split = box.split(percentage=0.3)
	split.label(text="設定値タイプ:")
	row = split.row(align=True)
	
	if type == 'tex':
		row.label(text='テクスチャ')
	elif type == 'col':
		row.label(text='色')
	elif type == 'f':
		row.label(text='値')
	
	row.prop(tex_slot, 'use', text="")
	sub_row = row.row(align=True)
	sub_row.prop(tex_slot, 'use_rgb_to_intensity', text="")
	if tex_slot.use:
		sub_row.enabled = False
	box.prop(tex, 'name', icon='SORTALPHA', text="設定値名")
	
	if type == "tex":
		if tex.type == 'IMAGE':
			img = tex.image
			if img:
				if img.source == 'FILE':
					sub_box = box.box()
					sub_box.prop(img, 'name', icon='IMAGE_DATA', text="テクスチャ名")
					if 'cm3d2_path' not in img.keys():
						img['cm3d2_path'] = "Assets\\texture\\texture\\" + os.path.basename(img.filepath)
					sub_box.prop(img, '["cm3d2_path"]', text="テクスチャパス")
					
					if len(img.pixels):
						sub_box.operator(show_image.bl_idname, text="この画像を表示", icon='ZOOM_IN').image_name = img.name
					else:
						sub_box.operator(replace_cm3d2_tex.bl_idname, icon='BORDERMOVE')
				#box.prop(tex_slot, 'color', text="")
				#box.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
	elif type == "col":
		sub_box = box.box()
		sub_box.prop(tex_slot, 'color', text="")
		sub_box.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
		sub_box.operator(sync_tex_color_ramps.bl_idname, icon='COLOR')
	elif type == "f":
		sub_box = box.box()
		sub_box.prop(tex_slot, 'diffuse_color_factor', icon='ARROW_LEFTRIGHT', text="値")
		split = sub_box.split(percentage=0.3)
		split.label(text="正確な値: ")
		split.label(text=str(tex_slot.diffuse_color_factor))
		sub_box.operator(sync_tex_color_ramps.bl_idname, icon='COLOR')
	
	base_name = common.remove_serial_number(tex.name)
	description = ""
	if base_name == '_MainTex':
		description = "面の色を決定するテクスチャを指定。\n普段テスクチャと呼んでいるものは基本コレです。\nテクスチャパスは適当でも動いたりしますが、\nテクスチャ名はきちんと決めましょう。"
	if base_name == '_ToonRamp':
		description = "面をトゥーン処理している\nグラデーション画像を指定します。"
	elif base_name == '_ShadowTex':
		description = "陰部分の面の色を決定するテクスチャを指定。\n「陰」とは光の当たる面の反対側のことで、\n別の物体に遮られてできるのは「影」とします。"
	if base_name == '_ShadowRateToon':
		description = "陰部分の面をトゥーン処理している\nグラデーション画像を指定します。"
	elif base_name == '_Color':
		description = "面の色を指定、白色で無効。\n_MainTexへ追加で色付けしたり、\n単色でよければここを設定しましょう。"
	elif base_name == '_ShadowColor':
		description = "影の色を指定、白色で無効。\n別の物体に遮られてできた「影」の色です。"
	elif base_name == '_RimColor':
		description = "リムライトの色を指定。\nリムライトとは縁にできる光の反射のことです。"
	elif base_name == '_OutlineColor':
		description = "輪郭線の色を指定。\n面の色が単色の場合は、\nそれを少し暗くしたものを指定してもいいかも。"
	elif base_name == '_Shininess':
		description = "スペキュラーの強さを指定。0.0～1.0で指定。\nスペキュラーとは面の角度と光源の角度によって\nできるハイライトのことです。\n金属、皮、ガラスなどに使うと良いでしょう。"
	elif base_name == '_OutlineWidth':
		description = "輪郭線の太さを指定。\n0.002は太め、0.001は細め。\n小数点第3位までしか表示されていませんが、\n内部にはそれ以下の数値も保存されています。"
	elif base_name == '_RimPower':
		description = "リムライトの強さを指定。\nこの値は1.0以上なことが多いです。\nこのアドオンではデフォルトは25としています。"
	elif base_name == '_RimShift':
		description = "リムライトの幅を指定。\n0.0～1.0で指定。0.5でもかなり強い。"
	elif base_name == '_RenderTex':
		description = "モザイクシェーダーにある設定値。\n特に設定の必要なし。"
	elif base_name == '_FloatValue1':
		description = "モザイクの大きさ？(未確認)"
	if description != "":
		sub_box = box.box()
		col = sub_box.column(align=True)
		col.label(text="解説", icon='TEXT')
		for line in description.split('\n'):
			col.label(text=line)

# ヘルプメニューに項目追加
def INFO_MT_help(self, context):
	self.layout.separator()
	self.layout.operator(update_cm3d2_converter.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.menu(INFO_MT_help_CM3D2_Converter_RSS_sub.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator(show_cm3d2_converter_preference.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
class INFO_MT_help_CM3D2_Converter_RSS_sub(bpy.types.Menu):
	bl_idname = "INFO_MT_help_CM3D2_Converter_RSS_sub"
	bl_label = "CM3D2 Converterの更新履歴"
	
	def draw(self, context):
		self.layout.menu(INFO_MT_help_CM3D2_Converter_RSS.bl_idname, text="取得に数秒かかります", icon='FILE_REFRESH')
class INFO_MT_help_CM3D2_Converter_RSS(bpy.types.Menu):
	bl_idname = "INFO_MT_help_CM3D2_Converter_RSS"
	bl_label = "CM3D2 Converterの更新履歴"
	
	def draw(self, context):
		try:
			import re, urllib, urllib.request, xml.sax.saxutils
			response = urllib.request.urlopen("https://github.com/CM3Duser/Blender-CM3D2-Converter/commits/master.atom")
			html = response.read().decode('utf-8')
			titles = re.findall(r'\<title\>[ 　\t\r\n]*([^ 　\t\<\>\r\n][^\<]*[^ 　\t\<\>\r\n])[ 　\t\r\n]*\<\/title\>', html)[1:]
			updates = re.findall(r'\<updated\>([^\<\>]*)\<\/updated\>', html)[1:]
			links = re.findall(r'<link [^\<\>]*href="([^"]+)"/>', html)[2:]
			count = 0
			for title, update, link in zip(titles, updates, links):
				title = xml.sax.saxutils.unescape(title, {'&quot;': '"'})
				
				rss_datetime = datetime.datetime.strptime(update[:-6], '%Y-%m-%dT%H:%M:%S')
				diff_seconds = datetime.datetime.now() - rss_datetime
				icon = 'SORTTIME'
				if 7 < diff_seconds.days:
					icon = 'NLA'
				elif 3 < diff_seconds.days:
					icon = 'COLLAPSEMENU'
				elif 1 <= diff_seconds.days:
					icon = 'TIME'
				elif diff_seconds.days == 0 and 60 * 60 < diff_seconds.seconds:
					icon = 'RECOVER_LAST'
				elif diff_seconds.seconds <= 60 * 60:
					icon = 'PREVIEW_RANGE'
				
				update = re.sub(r'^(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)\+(\d+):(\d+)', r'\2/\3 \4:\5', update)
				text = "(" + update + ") " + title
				self.layout.operator(open_url.bl_idname, text=text, icon=icon).url = link
				count += 1
		except TypeError:
			self.layout.label(text="更新の取得に失敗しました", icon='ERROR')