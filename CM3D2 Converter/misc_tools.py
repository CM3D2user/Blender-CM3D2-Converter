import os, re, sys, bpy, bmesh, mathutils, webbrowser, urllib, zipfile, subprocess, urllib.request, datetime

def ArrangeName(name, flag=True):
	if flag:
		return re.sub(r'\.\d{3}$', "", name)
	return name

# アドオンアップデート処理
class update_cm3d2_converter(bpy.types.Operator):
	bl_idname = 'script.update_cm3d2_converter'
	bl_label = "CM3D2 Converterを更新"
	bl_description = "GitHubから最新版のBlender-CM3D2-Converterをダウンロードし上書きします、実行した後は再起動して下さい"
	bl_options = {'REGISTER'}
	
	is_restart = bpy.props.BoolProperty(name="更新後にBlenderを再起動", description="アドオン更新後にBlenderを再起動します", default=True)
	is_toggle_console = bpy.props.BoolProperty(name="再起動後にコンソールを閉じる", default=True)
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_restart')
		self.layout.prop(self, 'is_toggle_console')
	
	def execute(self, context):
		response = urllib.request.urlopen("https://github.com/CM3Duser/Blender-CM3D2-Converter/archive/master.zip")
		tempDir = bpy.app.tempdir
		zipPath = os.path.join(tempDir, "Blender-CM3D2-Converter-master.zip")
		addonDir = os.path.dirname(__file__)
		f = open(zipPath, "wb")
		f.write(response.read())
		f.close()
		zf = zipfile.ZipFile(zipPath, "r")
		for f in zf.namelist():
			if not os.path.basename(f):
				pass
			else:
				if ("CM3D2 Converter" in f):
					uzf = open(os.path.join(addonDir, os.path.basename(f)), 'wb')
					uzf.write(zf.read(f))
					uzf.close()
		zf.close()
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
			self.report(type={'WARNING'}, message="Blender-CM3D2-Converterを更新しました、再起動して下さい")
		return {'FINISHED'}

class quick_vertex_group_transfer(bpy.types.Operator):
	bl_idname = 'object.quick_vertex_group_transfer'
	bl_label = "クイック・ウェイト転送"
	bl_description = "アクティブなメッシュに他の選択メッシュの頂点グループを転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	vertex_group_remove_all = bpy.props.BoolProperty(name="最初に頂点グループ全削除", default=True)
	vertex_group_clean = bpy.props.BoolProperty(name="ウェイト0.0の頂点はグループから除外", default=True)
	vertex_group_delete = bpy.props.BoolProperty(name="割り当ての無い頂点グループ削除", default=True)
	
	@classmethod
	def poll(cls, context):
		if (len(context.selected_objects) <= 1):
			return False
		source_objs = []
		for obj in context.selected_objects:
			if (obj.type == 'MESH' and context.object.name != obj.name):
				source_objs.append(obj)
		if (len(source_objs) <= 0):
			return False
		for obj in source_objs:
			if (1 <= len(obj.vertex_groups)):
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'vertex_group_remove_all')
		self.layout.prop(self, 'vertex_group_clean')
		self.layout.prop(self, 'vertex_group_delete')
	
	def execute(self, context):
		source_objs = []
		for obj in context.selected_objects:
			if (obj.type == 'MESH' and context.active_object.name != obj.name):
				source_objs.append(obj)
		if (0 < len(context.active_object.vertex_groups) and self.vertex_group_remove_all):
			bpy.ops.object.vertex_group_remove(all=True)
		me = context.active_object.data
		vert_mapping = 'NEAREST'
		for obj in source_objs:
			if (len(obj.data.polygons) <= 0):
				for obj2 in source_objs:
					if (len(obj.data.edges) <= 0):
						break
				else:
					vert_mapping = 'EDGEINTERP_NEAREST'
				break
		else:
			vert_mapping = 'POLYINTERP_NEAREST'
		try:
			bpy.ops.object.data_transfer(use_reverse_transfer=True, data_type='VGROUP_WEIGHTS', use_create=True, vert_mapping=vert_mapping, layers_select_src='ALL', layers_select_dst='NAME')
		except:
			bpy.ops.object.data_transfer(use_reverse_transfer=True, data_type='VGROUP_WEIGHTS', use_create=True, vert_mapping='NEAREST', layers_select_src='NAME', layers_select_dst='ALL')
		if (self.vertex_group_clean):
			bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0, keep_single=False)
		if (self.vertex_group_delete):
			obj = context.active_object
			for vg in obj.vertex_groups:
				for vert in obj.data.vertices:
					try:
						if (vg.weight(vert.index) > 0.0):
							break
					except RuntimeError:
						pass
				else:
					obj.vertex_groups.remove(vg)
		context.active_object.vertex_groups.active_index = 0
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
	mode = bpy.props.EnumProperty(items=items, name="対象頂点グループ", default='ACTIVE')
	blur_count = bpy.props.IntProperty(name="処理回数", default=5, min=1, max=100, soft_min=1, soft_max=100, step=1)
	use_clean = bpy.props.BoolProperty(name="ウェイト0.0の頂点は頂点グループから除外", default=True)
	
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
		self.layout.prop(self, 'blur_count')
		self.layout.prop(self, 'use_clean')
	
	def execute(self, context):
		activeObj = context.active_object
		pre_mode = activeObj.mode
		bpy.ops.object.mode_set(mode='OBJECT')
		me = activeObj.data
		target_weights = []
		if (self.mode == 'ACTIVE'):
			target_weights.append(activeObj.vertex_groups.active)
		elif (self.mode == 'ALL'):
			for vg in activeObj.vertex_groups:
				target_weights.append(vg)
		bm = bmesh.new()
		bm.from_mesh(me)
		context.window_manager.progress_begin(0, self.blur_count * len(target_weights) * len(bm.verts))
		total_count = 0
		for count in range(self.blur_count):
			for vg in target_weights:
				vg_index = vg.index
				new_weights = []
				for vert in bm.verts:
					context.window_manager.progress_update(total_count)
					total_count += 1
					for group in me.vertices[vert.index].groups:
						if (group.group == vg_index):
							my_weight = group.weight
							break
					else:
						my_weight = 0.0
					near_weights = []
					for edge in vert.link_edges:
						for v in edge.verts:
							if (v.index != vert.index):
								edges_vert = v
								break
						for group in me.vertices[edges_vert.index].groups:
							if (group.group == vg_index):
								near_weights.append(group.weight)
								break
						else:
							near_weights.append(0.0)
					near_weight_average = 0
					for weight in near_weights:
						near_weight_average += weight
					try:
						near_weight_average /= len(near_weights)
					except ZeroDivisionError:
						near_weight_average = 0.0
					new_weights.append( (my_weight*2 + near_weight_average) / 3 )
				for vert, weight in zip(me.vertices, new_weights):
					if (self.use_clean and weight <= 0.000001):
						vg.remove([vert.index])
					else:
						vg.add([vert.index], weight, 'REPLACE')
		bm.free()
		bpy.ops.object.mode_set(mode=pre_mode)
		context.window_manager.progress_end()
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
		convert_count = 0
		for vg in ob.vertex_groups:
			direction = re.search(r'[_ ]([rRlL])[_ ]', vg.name)
			if direction:
				direction = direction.groups()[0]
				vg_name = re.sub(r'([_ ])[rRlL]([_ ])', r'\1*\2', vg.name) + "." + direction
				#self.report(type={'INFO'}, message=vg.name +" → "+ vg_name)
				vg.name = vg_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message=str(convert_count) + "個の頂点グループ名をBlender用に変換しました")
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
		convert_count = 0
		for vg in ob.vertex_groups:
			if vg.name.count('*') == 1:
				direction = re.search(r'\.([rRlL])$', vg.name)
				if direction:
					direction = direction.groups()[0]
					vg_name = re.sub(r'\.[rRlL]$', '', vg.name).replace('*', direction)
					vg_name = re.sub(r'([_ ])\*([_ ])', r'\1'+direction+r'\2', vg_name)
					#self.report(type={'INFO'}, message=vg.name +" → "+ vg_name)
					vg.name = vg_name
					convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message=str(convert_count) + "個の頂点グループ名をCM3D2用に戻しました")
		return {'FINISHED'}

class shape_key_transfer_ex(bpy.types.Operator):
	bl_idname = 'object.shape_key_transfer_ex'
	bl_label = "シェイプキー強制転送"
	bl_description = "頂点数の違うメッシュ同士でも一番近い頂点からシェイプキーを強制転送します"
	bl_options = {'REGISTER', 'UNDO'}
	
	remove_empty_shape = bpy.props.BoolProperty(name="全頂点に変形のないシェイプを削除", default=True)
	
	@classmethod
	def poll(cls, context):
		if len(context.selected_objects) != 2:
			return False
		for ob in context.selected_objects:
			if ob.type != 'MESH':
				return False
			if ob.name != context.active_object.name:
				if not ob.data.shape_keys:
					return False
		if context.active_object.mode != 'OBJECT':
			return False
		return True
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'remove_empty_shape')
	
	def execute(self, context):
		target_ob = context.active_object
		for ob in context.selected_objects:
			if ob.name != target_ob.name:
				source_ob = ob
		bm = bmesh.new()
		bm.from_mesh(source_ob.data)
		bm.faces.ensure_lookup_table()
		kd = mathutils.kdtree.KDTree(len(bm.verts))
		for i, vert in enumerate(bm.verts):
			kd.insert(source_ob.matrix_world * vert.co.copy(), i)
		kd.balance()
		is_first = True
		context.window_manager.progress_begin(0, len(source_ob.data.shape_keys.key_blocks) * len(target_ob.data.vertices))
		count = 0
		for key_block in source_ob.data.shape_keys.key_blocks:
			if is_first:
				is_first = False
				if not target_ob.data.shape_keys:
					target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
				continue
			if key_block.name not in target_ob.data.shape_keys.key_blocks.keys():
				target_shape = target_ob.shape_key_add(name=key_block.name, from_mix=False)
			else:
				target_shape = target_ob.data.shape_keys.key_blocks[key_block.name]
			is_shaped = False
			for target_vert in target_ob.data.vertices:
				co, index, dist = kd.find(target_ob.matrix_world * target_vert.co)
				total_diff = key_block.data[index].co - source_ob.data.vertices[index].co
				target_shape.data[target_vert.index].co = target_ob.data.vertices[target_vert.index].co + total_diff
				if not is_shaped and 0.001 <= total_diff.length:
					is_shaped = True
				context.window_manager.progress_update(count)
				count += 1
			if not is_shaped and self.remove_empty_shape:
				target_ob.shape_key_remove(target_shape)
		target_ob.active_shape_key_index = 0
		context.window_manager.progress_end()
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
	bl_description = "シェイプキーの変形をぼかしてなめらかにします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象シェイプキー", default='ACTIVE')
	strength = bpy.props.IntProperty(name="処理回数", description="ぼかしの強度(回数)を設定します", default=5, min=1, max=100, soft_min=1, soft_max=100, step=1)
	
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
		self.layout.prop(self, 'mode')
		self.layout.prop(self, 'strength')
	
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
		total_count = 0
		for i, vert in enumerate(bm.verts):
			near_verts = []
			for edge in vert.link_edges:
				for v in edge.verts:
					if vert.index != v.index:
						near_verts.append(v)
						break
			for shape in target_shapes:
				for s in range(self.strength):
					context.window_manager.progress_update(total_count)
					total_count += 1
					data = shape.data
					average = mathutils.Vector((0, 0, 0))
					for v in near_verts:
						average += data[v.index].co - me.vertices[v.index].co
					average /= len(near_verts)
					co = data[i].co - vert.co
					data[i].co = ((co * 2) + average) / 3 + vert.co
		bpy.ops.object.mode_set(mode=pre_mode)
		context.window_manager.progress_end()
		return {'FINISHED'}

class radius_blur_shape_key(bpy.types.Operator):
	bl_idname = 'object.radius_blur_shape_key'
	bl_label = "シェイプキー範囲ぼかし"
	bl_description = "シェイプキーの変形を範囲でぼかしてなめらかにします"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('ACTIVE', "アクティブのみ", "", 1),
		('ALL', "全て", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="対象シェイプキー", default='ACTIVE')
	radius_multi = bpy.props.FloatProperty(name="範囲：辺の長さの平均×", default=2, min=0.1, max=10, soft_min=0.1, soft_max=10, step=10, precision=1)
	blur_count = bpy.props.IntProperty(name="処理回数", default=5, min=1, max=100, soft_min=1, soft_max=100, step=1)
	fadeout = bpy.props.BoolProperty(name="距離で影響減退", default=False)
	
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
		self.layout.prop(self, 'mode')
		self.layout.prop(self, 'radius_multi')
		self.layout.prop(self, 'blur_count')
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
		kd = mathutils.kdtree.KDTree(len(me.vertices))
		for i, v in enumerate(me.vertices):
			kd.insert(v.co, i)
		kd.balance()
		context.window_manager.progress_begin(0, self.blur_count * len(target_shapes) * len(me.vertices))
		total_count = 0
		for count in range(self.blur_count):
			for shape in target_shapes:
				data = shape.data
				new_co = []
				for vert in me.vertices:
					context.window_manager.progress_update(total_count)
					total_count += 1
					average_co = mathutils.Vector((0, 0, 0))
					nears = kd.find_range(vert.co, radius)
					nears_total = 0
					for co, index, dist in nears:
						if self.fadeout:
							diff = co - vert.co
							multi = (radius - diff.length) / radius
							average_co += (data[index].co - me.vertices[index].co) * multi
							nears_total += multi
						else:
							average_co += data[index].co - me.vertices[index].co
							nears_total += 1
					average_co /= nears_total
					co = data[vert.index].co - vert.co
					new_co.append(((co * 2) + average_co) / 3 + vert.co)
					#data[vert.index].co = ((co * 2) + average_co) / 3 + vert.co
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
	
	@classmethod
	def poll(cls, context):
		if 'material' in dir(context):
			if not context.material:
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		if not re.search(r'^[^\.]+\.[^\.]+$', context.active_object.name):
			self.layout.label(text="オブジェクト名を設定してからの作成を推奨", icon='CANCEL')
		self.layout.separator()
		self.layout.prop(self, 'type')
		self.layout.prop(self, 'is_decorate')
	
	def execute(self, context):
		ob = context.active_object
		ob_names = ob.name.split('.')
		if not context.material_slot:
			bpy.ops.object.material_slot_add()
		mate = context.blend_data.materials.new(ob_names[0])
		context.material_slot.material = mate
		tex_list, col_list, f_list = [], [], []
		#mate.use_face_texture = True
		
		if False:
			pass
		elif self.type == 'CM3D2/Toony_Lighted_Outline':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Outline'
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
			tex_list.append(("_HiTex", ob_names[0] + "_s", "Assets\\texture\\texture\\" + ob_names[0] + "_s.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_OutlineColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 1))
			f_list.append(("_OutlineWidth", 0.002))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
		elif self.type == 'Unlit/Transparent':
			mate['shader1'] = 'Unlit/Transparent'
			mate['shader2'] = 'Unlit__Transparent'
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			col_list.append(("_Color", (1, 1, 1, 1)))
		elif self.type == 'CM3D2/Toony_Lighted_Trans_NoZ':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Trans_NoZ'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Trans_NoZ'
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
		elif self.type == 'CM3D2/Toony_Lighted':
			mate['shader1'] = 'CM3D2/Toony_Lighted'
			mate['shader2'] = 'CM3D2__Toony_Lighted'
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
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
			tex_list.append(("_MainTex", ob_names[0], "Assets\\texture\\texture\\" + ob_names[0] + ".png"))
			tex_list.append(("_ToonRamp", "toonGrayA1", r"Assets\texture\texture\toon\toonGrayA1.png"))
			tex_list.append(("_ShadowTex", ob_names[0] + "_shadow", "Assets\\texture\\texture\\" + ob_names[0] + "_shadow.png"))
			tex_list.append(("_ShadowRateToon", "toonDress_shadow", r"Assets\texture\texture\toon\toonDress_shadow.png"))
			tex_list.append(("_HiTex", ob_names[0] + "_s", "Assets\\texture\\texture\\" + ob_names[0] + "_s.png"))
			col_list.append(("_Color", (1, 1, 1, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			col_list.append(("_RimColor", (0.5, 0.5, 0.5, 1)))
			col_list.append(("_ShadowColor", (0, 0, 0, 1)))
			f_list.append(("_Shininess", 0))
			f_list.append(("_RimPower", 25))
			f_list.append(("_RimShift", 0))
			f_list.append(("_HiRate", 0.5))
			f_list.append(("_HiPow", 0.001))
		
		if self.is_decorate:
			shader_type = self.type
			if '/Toony_' in shader_type:
				mate.diffuse_shader = 'TOON'
				mate.diffuse_toon_smooth = 0.01
				mate.diffuse_toon_size = 1.2
			if 'Trans' in  shader_type:
				mate.use_transparency = True
				mate.alpha = 0.5
			if 'CM3D2/Man' in shader_type:
				mate.use_shadeless = True
			if 'Unlit/' in shader_type:
				mate.emit = 0.5
			if '_NoZ' in shader_type:
				mate.offset_z = 9999
			if 'CM3D2/Mosaic' in shader_type:
				mate.use_transparency = True
				mate.transparency_method = 'RAYTRACE'
				mate.alpha = 0.25
				mate.raytrace_transparency.ior = 2
		
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
			img.source = 'FILE'
			tex.image = img
			slot_count += 1
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
			direction = re.search(r'[_ ]([rRlL])[_ ]', bone.name)
			if direction:
				direction = direction.groups()[0]
				bone_name = re.sub(r'([_ ])[rRlL]([_ ])', r'\1*\2', bone.name) + "." + direction
				#self.report(type={'INFO'}, message=bone.name +" → "+ bone_name)
				bone.name = bone_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message=str(convert_count) + "個のボーン名をBlender用に変換しました")
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
			if bone.name.count('*') == 1:
				direction = re.search(r'\.([rRlL])$', bone.name)
				if direction:
					direction = direction.groups()[0]
					bone_name = re.sub(r'\.[rRlL]$', '', bone.name)
					bone_name = re.sub(r'([_ ])\*([_ ])', r'\1'+direction+r'\2', bone_name)
					#self.report(type={'INFO'}, message=bone.name +" → "+ bone_name)
					bone.name = bone_name
					convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message=str(convert_count) + "個のボーン名をCM3D2用に戻しました")
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

class show_apply_modifier_addon_web(bpy.types.Operator):
	bl_idname = "object.show_apply_modifier_addon_web"
	bl_label = "モディファイアを適用できない場合"
	bl_description = "Apply ModifierのWEBサイトを開きます"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		webbrowser.open("https://sites.google.com/site/matosus304blendernotes/home/download#apply_modifier")
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



# 頂点グループメニューに項目追加
def MESH_MT_vertex_group_specials(self, context):
	self.layout.separator()
	self.layout.operator(quick_vertex_group_transfer.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.separator()
	self.layout.operator(blur_vertex_group.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.operator(radius_blur_vertex_group.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.separator()
	self.layout.operator(convert_cm3d2_vertex_group_names.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value, text="頂点グループ名を CM3D2 → Blender")
	self.layout.operator(convert_cm3d2_vertex_group_names_restore.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value, text="頂点グループ名を Blender → CM3D2")

# シェイプメニューに項目追加
def MESH_MT_shape_key_specials(self, context):
	self.layout.separator()
	self.layout.operator(shape_key_transfer_ex.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.separator()
	self.layout.operator(scale_shape_key.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.separator()
	self.layout.operator(blur_shape_key.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.operator(radius_blur_shape_key.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)

# マテリアルタブに項目追加
def MATERIAL_PT_context_material(self, context):
	mate = context.material
	if not mate:
		self.layout.operator(new_cm3d2.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	else:
		if 'shader1' in mate.keys() and 'shader2' in mate.keys():
			box = self.layout.box()
			#row = box.split(percentage=0.3)
			row = box.row()
			row.label(text="CM3D2用", icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
			row.operator('material.export_cm3d2_mate', icon='SAVE_AS', text="")
			
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
					col.label(text="CM3D2用 ボーン名変換", icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
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
				row.label(text="CM3D2用ボーン情報", icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
				sub_row = row.row()
				sub_row.alignment = 'RIGHT'
				if bone_data_count:
					sub_row.label(text=str(bone_data_count)+"個", icon='CHECKBOX_HLT')
				else:
					sub_row.label(text="0個", icon='CHECKBOX_DEHLT')
				row = col.row(align=True)
				row.operator(copy_armature_bone_data_property.bl_idname, icon='COPYDOWN', text="コピー")
				row.operator(paste_armature_bone_data_property.bl_idname, icon='PASTEDOWN', text="貼り付け")
				row.operator(remove_armature_bone_data_property.bl_idname, icon='X', text="")

# オブジェクトタブに項目追加
def OBJECT_PT_context_object(self, context):
	ob = context.active_object
	if ob:
		if ob.type == 'MESH':
			row = self.layout.row(align=True)
			if re.search(r'^[^\.]+\.[^\.]+$', ob.name):
				name, base = ob.name.split('.')
				row.label(text="model名: " + name, icon='SORTALPHA')
				row.label(text="基点ボーン名: " + base, icon='CONSTRAINT_BONE')
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
				row.label(text="CM3D2用ボーン情報", icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
				sub_row = row.row()
				sub_row.alignment = 'RIGHT'
				if 'BoneData:0' in ob.keys() and 'LocalBoneData:0' in ob.keys():
					bone_data_count = 0
					for key in ob.keys():
						if re.search(r'^(Local)?BoneData:\d+$', key):
							bone_data_count += 1
					sub_row.label(text=str(bone_data_count)+"個", icon='CHECKBOX_HLT')
				else:
					sub_row.label(text="0個", icon='CHECKBOX_DEHLT')
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
				if me.shape_keys:
					if len(ob.modifiers):
						self.layout.operator(show_apply_modifier_addon_web.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)

# テキストヘッダーに項目追加
def TEXT_HT_header(self, context):
	texts = bpy.data.texts
	text_keys = texts.keys()
	self.layout.label(text="CM3D2用:", icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	row = self.layout.row(align=True)
	if 'BoneData' in text_keys:
		txt = bpy.data.texts['BoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator(show_text.bl_idname, icon='ARMATURE_DATA', text="BoneData (" + str(line_count) + "行)").name = 'BoneData'
	if 'LocalBoneData' in text_keys:
		txt = bpy.data.texts['LocalBoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator(show_text.bl_idname, icon='BONE_DATA', text="LocalBoneData (" + str(line_count) + "行)").name = 'LocalBoneData'
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
	if tex_slot.use:
		type = "tex"
	else:
		if tex_slot.use_rgb_to_intensity:
			type = "col"
		else:
			type = "f"
	box = self.layout.box()
	box.label(text="CM3D2用", icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	row = box.row(align=True)
	row.label(text="設定値タイプ: " + type)
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
					box.prop(img, 'name', icon='IMAGE_DATA', text="テクスチャ名")
					box.prop(img, 'filepath', text="テクスチャパス")
				#box.prop(tex_slot, 'color', text="")
				#box.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
	elif type == "col":
		box.prop(tex_slot, 'color', text="")
		box.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
	elif type == "f":
		box.prop(tex_slot, 'diffuse_color_factor', icon='ARROW_LEFTRIGHT', text="値")
	
	base_name = ArrangeName(tex.name)
	description = ""
	if base_name == '_MainTex':
		description = "面の色を決定するテクスチャを指定。\n普段テスクチャと呼んでいるものは基本コレです。\nテクスチャパスは適当でも動いたりしますが、\nテクスチャ名はきちんと決めましょう。"
	elif base_name == '_ShadowTex':
		description = "陰部分の面の色を決定するテクスチャを指定。\n「陰」とは光の当たる面の反対側のことで、\n別の物体に遮られてできるのは「影」とします。"
	elif base_name == '_Color':
		description = "面の色を指定、白色で無効。\n_MainTexへ追加で色付けしたり、\n単色でよければここを設定しましょう。"
	elif base_name == '_ShadowColor':
		description = "影の色を指定、白色で無効。\n別の物体に遮られてできた「影」の色です。"
	elif base_name == '_RimColor':
		description = "リムライトの色を指定。\nリムライトとは縁にできる光の反射のことです。"
	elif base_name == '_OutlineColor':
		description = "輪郭線の色を指定。\n面の色が単色の場合は、\nそれを少し暗くしたものを指定してもいいかも。"
	elif base_name == '_Shininess':
		description = "スペキュラーの強さを指定。\nスペキュラーとは面の角度と光源の角度によって\nできるハイライトのことです。\n金属、皮、ガラスなどに使うと良いでしょう。"
	elif base_name == '_OutlineWidth':
		description = "輪郭線の太さを指定。\n0.002は太め、0.001は細め。"
	elif base_name == '_RimPower':
		description = "リムライトの強さを指定。\nこの値は1.0以上なことが多いです。\nこのアドオンではデフォルトは25としています。"
	elif base_name == '_RimShift':
		description = "リムライトの幅を指定。\n0.0～1.0で指定。0.5でもかなり強い。"
	if description != "":
		sub_box = box.box()
		col = sub_box.column(align=True)
		col.label(text="解説", icon='TEXT')
		for line in description.split('\n'):
			col.label(text=line)

# ヘルプメニューに項目追加
def INFO_MT_help(self, context):
	self.layout.separator()
	self.layout.operator(update_cm3d2_converter.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
	self.layout.menu(INFO_MT_help_CM3D2_Converter_RSS.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
class INFO_MT_help_CM3D2_Converter_RSS(bpy.types.Menu):
	bl_idname = "INFO_MT_help_CM3D2_Converter_RSS"
	bl_label = "CM3D2 Converterの更新履歴 (取得に数秒)"
	
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