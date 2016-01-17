import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	mate = context.material
	if not mate:
		col = self.layout.column(align=True)
		col.operator('material.new_cm3d2', icon_value=common.preview_collections['main']['KISS'].icon_id)
		row = col.row(align=True)
		row.operator('material.import_cm3d2_mate', icon='FILE_FOLDER', text="mateから")
		row.operator('material.paste_material', icon='PASTEDOWN', text="クリップボードから")
	else:
		if 'shader1' in mate.keys() and 'shader2' in mate.keys():
			box = self.layout.box()
			#row = box.split(percentage=0.3)
			row = box.split(percentage=0.5)
			row.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			sub_row = row.row(align=True)
			sub_row.operator('material.export_cm3d2_mate', icon='FILE_FOLDER', text="mateへ")
			sub_row.operator('material.copy_material', icon='COPYDOWN', text="コピー")
			
			type_name = "不明"
			icon = 'ERROR'
			if mate['shader1'] == 'CM3D2/Toony_Lighted':
				type_name = "トゥーン"
				icon = 'SOLID'
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Hair':
				type_name = "トゥーン 髪"
				icon = 'PARTICLEMODE'
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Trans':
				type_name = "トゥーン 透過"
				icon = 'WIRE'
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Trans_NoZ':
				type_name = "トゥーン 透過 NoZ"
				icon = 'DRIVER'
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Outline':
				type_name = "トゥーン 輪郭線"
				icon = 'ANTIALIASED'
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Hair_Outline':
				type_name = "トゥーン 輪郭線 髪"
				icon = 'PARTICLEMODE'
			elif mate['shader1'] == 'CM3D2/Toony_Lighted_Outline_Trans':
				type_name = "トゥーン 輪郭線 透過"
				icon = 'PROP_OFF'
			elif mate['shader1'] == 'CM3D2/Lighted_Trans':
				type_name = "透過"
				icon = 'VISIBLE_IPO_OFF'
			elif mate['shader1'] == 'Unlit/Texture':
				type_name = "発光"
				icon = 'PARTICLES'
			elif mate['shader1'] == 'Unlit/Transparent':
				type_name = "発光 透過"
				icon = 'MOD_PARTICLES'
			elif mate['shader1'] == 'CM3D2/Mosaic':
				type_name = "モザイク"
				icon = 'ALIASED'
			elif mate['shader1'] == 'CM3D2/Man':
				type_name = "ご主人様"
				icon = 'ARMATURE_DATA'
			elif mate['shader1'] == 'Diffuse':
				type_name = "リアル"
				icon = 'BRUSH_CLAY_STRIPS'
			elif mate['shader1'] == 'Transparent/Diffuse':
				type_name = "リアル 透過"
				icon = 'MATCAP_09'
			elif mate['shader1'] == 'CM3D2_Debug/Debug_CM3D2_Normal2Color':
				type_name = "法線"
				icon = 'MATCAP_23'
			
			row = box.split(percentage=0.333333333333333333333)
			row.label(text="種類:")
			row.label(text=type_name, icon=icon)
			box.prop(mate, 'name', icon='SORTALPHA', text="マテリアル名")
			box.prop(mate, '["shader1"]', icon='MATERIAL', text="シェーダー1")
			box.prop(mate, '["shader2"]', icon='SMOOTH', text="シェーダー2")
			
			box.operator('material.decorate_material', icon='TEXTURE_SHADED')
			
			
			if 'CM3D2 Texture Expand' not in mate.keys():
				mate['CM3D2 Texture Expand'] = True
			box = self.layout.box()
			if mate['CM3D2 Texture Expand']:
				
				row = box.row()
				row.alignment = 'LEFT'
				op = row.operator('wm.context_set_int', icon='DOWNARROW_HLT', text="", emboss=False)
				op.data_path, op.value, op.relative = 'material["CM3D2 Texture Expand"]', 0, False
				row.label(text="簡易テクスチャ情報", icon_value=common.preview_collections['main']['KISS'].icon_id)
				
				for slot in mate.texture_slots:
					if not slot: continue
					if not slot.texture: continue
					tex = slot.texture
					name = common.remove_serial_number(tex.name).replace("_", "") + " "
					
					if slot.use: type = 'tex'
					else: type = 'col' if slot.use_rgb_to_intensity else 'f'
					
					if type == 'tex':
						row = box.row(align=True)
						sub_row = row.split(percentage=0.333333333333333333333, align=True)
						sub_row.label(text=name, icon_value=sub_row.icon(tex))
						if 'image' in dir(tex):
							if tex.image:
								sub_row.template_ID(tex, 'image')
						row.operator('material.quick_texture_show', text="", icon='RIGHTARROW').texture_name = tex.name
					elif type == 'col':
						row = box.row(align=True)
						sub_row = row.split(percentage=0.333333333333333333333, align=True)
						sub_row.label(text=name, icon_value=sub_row.icon(tex))
						sub_row.prop(slot, 'color', text="")
						sub_row.prop(slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="透明度", slider=True)
						row.operator('material.quick_texture_show', text="", icon='RIGHTARROW').texture_name = tex.name
					elif type == 'f':
						row = box.row(align=True)
						sub_row = row.split(percentage=0.333333333333333333333, align=True)
						sub_row.label(text=name, icon_value=sub_row.icon(tex))
						sub_row.prop(slot, 'diffuse_color_factor', icon='ARROW_LEFTRIGHT', text="値")
						row.operator('material.quick_texture_show', text="", icon='RIGHTARROW').texture_name = tex.name
				
				box.operator('texture.sync_tex_color_ramps', icon='LINKED')
			
			else:
				row = box.row()
				row.alignment = 'LEFT'
				op = row.operator('wm.context_set_int', icon='RIGHTARROW', text="", emboss=False)
				op.data_path, op.value, op.relative = 'material["CM3D2 Texture Expand"]', 1, False
				row.label(text="簡易テクスチャ情報", icon_value=common.preview_collections['main']['KISS'].icon_id)
		
		else:
			self.layout.operator('material.new_cm3d2', text="CM3D2用に変更", icon_value=common.preview_collections['main']['KISS'].icon_id)

class new_cm3d2(bpy.types.Operator):
	bl_idname = 'material.new_cm3d2'
	bl_label = "CM3D2用マテリアルを新規作成"
	bl_description = "Blender-CM3D2-Converterで使用できるマテリアルを新規で作成します"
	bl_options = {'REGISTER', 'UNDO'}
	
	items = [
		('CM3D2/Toony_Lighted', "トゥーン", "", 'SOLID', 0),
		('CM3D2/Toony_Lighted_Hair', "トゥーン 髪", "", 'PARTICLEMODE', 1),
		('CM3D2/Toony_Lighted_Trans', "トゥーン 透過", "", 'WIRE', 2),
		('CM3D2/Toony_Lighted_Trans_NoZ', "トゥーン 透過 NoZ", "", 'DRIVER', 3),
		('CM3D2/Toony_Lighted_Outline', "トゥーン 輪郭線", "", 'ANTIALIASED', 4),
		('CM3D2/Toony_Lighted_Hair_Outline', "トゥーン 輪郭線 髪", "", 'PARTICLEMODE', 5),
		('CM3D2/Toony_Lighted_Outline_Trans', "トゥーン 輪郭線 透過", "", 'PROP_OFF', 6),
		('CM3D2/Lighted_Trans', "透過", "", 'VISIBLE_IPO_OFF', 7),
		('Unlit/Texture', "発光", "", 'PARTICLES', 8),
		('Unlit/Transparent', "発光 透過", "", 'MOD_PARTICLES', 9),
		('CM3D2/Mosaic', "モザイク", "", 'ALIASED', 10),
		('CM3D2/Man', "ご主人様", "", 'ARMATURE_DATA', 11),
		('Diffuse', "リアル", "", 'BRUSH_CLAY_STRIPS', 12),
		('Transparent/Diffuse', "リアル 透過", "", 'MATCAP_09', 13),
		('CM3D2_Debug/Debug_CM3D2_Normal2Color', "法線", "", 'MATCAP_23', 14),
		]
	type = bpy.props.EnumProperty(items=items, name="種類", default='CM3D2/Toony_Lighted_Outline')
	is_decorate = bpy.props.BoolProperty(name="種類に合わせてマテリアルを装飾", default=True)
	is_replace_cm3d2_tex = bpy.props.BoolProperty(name="テクスチャを探す", default=False, description="CM3D2本体のインストールフォルダからtexファイルを探して開きます")
	
	@classmethod
	def poll(cls, context):
		return True
	
	def invoke(self, context, event):
		self.is_replace_cm3d2_tex = common.preferences().is_replace_cm3d2_tex
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.separator()
		self.layout.prop(self, 'type', icon='MATERIAL')
		self.layout.prop(self, 'is_decorate', icon='TEXTURE_SHADED')
		self.layout.prop(self, 'is_replace_cm3d2_tex', icon='BORDERMOVE')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		ob_names = common.remove_serial_number(ob.name).split('.')
		ob_name = ob_names[0]
		
		if context.material:
			mate = context.material
			for index, slot in enumerate(mate.texture_slots):
				mate.texture_slots.clear(index)
		else:
			if not context.material_slot:
				bpy.ops.object.material_slot_add()
			mate = context.blend_data.materials.new(ob_name)
		
		context.material_slot.material = mate
		tex_list, col_list, f_list = [], [], []
		
		base_path = "Assets\\texture\\texture\\"
		pref = common.preferences()
		
		_MainTex = ("_MainTex", ob_name, base_path + ob_name + ".png")
		_ToonRamp = ("_ToonRamp", pref.new_mate_toonramp_name, pref.new_mate_toonramp_path)
		_ShadowTex = ("_ShadowTex", ob_name + "_shadow", base_path + ob_name + "_shadow.png")
		_ShadowRateToon = ("_ShadowRateToon", pref.new_mate_shadowratetoon_name, pref.new_mate_shadowratetoon_path)
		_HiTex = ("_HiTex", ob_name + "_s", base_path + ob_name + "_s.png")
		
		_Color = ("_Color", pref.new_mate_color)
		_ShadowColor = ("_ShadowColor", pref.new_mate_shadowcolor)
		_RimColor = ("_RimColor", pref.new_mate_rimcolor)
		_OutlineColor = ("_OutlineColor", pref.new_mate_outlinecolor)
		
		_Shininess = ("_Shininess", pref.new_mate_shininess)
		_OutlineWidth = ("_OutlineWidth", pref.new_mate_outlinewidth)
		_RimPower = ("_RimPower", pref.new_mate_rimpower)
		_RimShift = ("_RimShift", pref.new_mate_rimshift)
		_HiRate = ("_HiRate", pref.new_mate_hirate)
		_HiPow = ("_HiPow", pref.new_mate_hipow)
		
		if False:
			pass
		elif self.type == 'CM3D2/Toony_Lighted_Outline':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Outline'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			col_list.append(_OutlineColor)
			f_list.append(_Shininess)
			f_list.append(_OutlineWidth)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2/Toony_Lighted_Trans':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Trans'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Trans'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			f_list.append(_Shininess)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2/Toony_Lighted_Hair_Outline':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Hair_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Hair_Outline'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			tex_list.append(_HiTex)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			col_list.append(_OutlineColor)
			f_list.append(_Shininess)
			f_list.append(_OutlineWidth)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
			f_list.append(_HiRate)
			f_list.append(_HiPow)
		elif self.type == 'CM3D2/Mosaic':
			mate['shader1'] = 'CM3D2/Mosaic'
			mate['shader2'] = 'CM3D2__Mosaic'
			tex_list.append(("_RenderTex", ""))
			f_list.append(("_FloatValue1", 30))
		elif self.type == 'Unlit/Texture':
			mate['shader1'] = 'Unlit/Texture'
			mate['shader2'] = 'Unlit__Texture'
			tex_list.append(_MainTex)
			col_list.append(_Color)
		elif self.type == 'Unlit/Transparent':
			mate['shader1'] = 'Unlit/Transparent'
			mate['shader2'] = 'Unlit__Transparent'
			tex_list.append(_MainTex)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			f_list.append(_Shininess)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2/Man':
			mate['shader1'] = 'CM3D2/Man'
			mate['shader2'] = 'CM3D2__Man'
			col_list.append(_Color)
			f_list.append(("_FloatValue2", 0.5))
			f_list.append(("_FloatValue3", 1))
		elif self.type == 'Diffuse':
			mate['shader1'] = 'Diffuse'
			mate['shader2'] = 'Diffuse'
			tex_list.append(_MainTex)
			col_list.append(_Color)
		elif self.type == 'CM3D2/Toony_Lighted_Trans_NoZ':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Trans_NoZ'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Trans_NoZ'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			col_list.append(_OutlineColor)
			f_list.append(_Shininess)
			f_list.append(_OutlineWidth)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2/Toony_Lighted_Outline_Trans':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Outline_Trans'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Outline_Trans'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			col_list.append(_OutlineColor)
			f_list.append(_Shininess)
			f_list.append(_OutlineWidth)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2/Lighted_Trans':
			mate['shader1'] = 'CM3D2/Lighted_Trans'
			mate['shader2'] = 'CM3D2__Lighted_Trans'
			tex_list.append(_MainTex)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			f_list.append(_Shininess)
		elif self.type == 'CM3D2/Toony_Lighted':
			mate['shader1'] = 'CM3D2/Toony_Lighted'
			mate['shader2'] = 'CM3D2__Toony_Lighted'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			f_list.append(_Shininess)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2/Toony_Lighted_Hair':
			mate['shader1'] = 'CM3D2/Toony_Lighted_Hair_Outline'
			mate['shader2'] = 'CM3D2__Toony_Lighted_Hair_Outline'
			tex_list.append(_MainTex)
			tex_list.append(_ToonRamp)
			tex_list.append(_ShadowTex)
			tex_list.append(_ShadowRateToon)
			tex_list.append(_HiTex)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			f_list.append(_Shininess)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
			f_list.append(_HiRate)
			f_list.append(_HiPow)
		elif self.type == 'Transparent/Diffuse':
			mate['shader1'] = 'Transparent/Diffuse'
			mate['shader2'] = 'Transparent__Diffuse'
			tex_list.append(_MainTex)
			col_list.append(_Color)
			col_list.append(_ShadowColor)
			col_list.append(_RimColor)
			col_list.append(_OutlineColor)
			f_list.append(_Shininess)
			f_list.append(_OutlineWidth)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		elif self.type == 'CM3D2_Debug/Debug_CM3D2_Normal2Color':
			mate['shader1'] = 'CM3D2_Debug/Debug_CM3D2_Normal2Color'
			mate['shader2'] = 'CM3D2_Debug__Debug_CM3D2_Normal2Color'
			col_list.append(_Color)
			col_list.append(_RimColor)
			col_list.append(_OutlineColor)
			col_list.append(("_SpecColor", (1, 1, 1, 1)))
			f_list.append(_Shininess)
			f_list.append(_OutlineWidth)
			f_list.append(_RimPower)
			f_list.append(_RimShift)
		
		tex_storage_files = common.get_tex_storage_files()
		slot_count = 0
		for data in tex_list:
			slot = mate.texture_slots.create(slot_count)
			tex = context.blend_data.textures.new(data[0], 'IMAGE')
			slot.texture = tex
			if data[1] == "":
				slot_count += 1
				continue
			slot.color = pref.new_mate_tex_color[:3]
			slot.diffuse_color_factor = pref.new_mate_tex_color[3]
			img = context.blend_data.images.new(data[1], 128, 128)
			img.filepath = data[2]
			img['cm3d2_path'] = data[2]
			img.source = 'FILE'
			tex.image = img
			slot_count += 1
			
			# tex探し
			if self.is_replace_cm3d2_tex:
				if common.replace_cm3d2_tex(img, tex_storage_files) and data[0]=='_MainTex':
					for face in me.polygons:
						if face.material_index == ob.active_material_index:
							me.uv_textures.active.data[face.index].image = img
		
		for data in col_list:
			slot = mate.texture_slots.create(slot_count)
			mate.use_textures[slot_count] = False
			slot.color = data[1][:3]
			slot.diffuse_color_factor = data[1][3]
			slot.use_rgb_to_intensity = True
			tex = context.blend_data.textures.new(data[0], 'BLEND')
			slot.texture = tex
			slot_count += 1
		
		for data in f_list:
			slot = mate.texture_slots.create(slot_count)
			mate.use_textures[slot_count] = False
			slot.diffuse_color_factor = data[1]
			tex = context.blend_data.textures.new(data[0], 'BLEND')
			slot.texture = tex
			slot_count += 1
		
		common.decorate_material(mate, self.is_decorate, me, ob.active_material_index)
		return {'FINISHED'}

class paste_material(bpy.types.Operator):
	bl_idname = 'material.paste_material'
	bl_label = "クリップボードからマテリアルを貼り付け"
	bl_description = "クリップボード内のマテリアル情報から新規マテリアルを作成します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_decorate = bpy.props.BoolProperty(name="種類に合わせてマテリアルを装飾", default=True)
	is_replace_cm3d2_tex = bpy.props.BoolProperty(name="テクスチャを探す", default=False, description="CM3D2本体のインストールフォルダからtexファイルを探して開きます")
	
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
		self.is_replace_cm3d2_tex = common.preferences().is_replace_cm3d2_tex
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_decorate')
		self.layout.prop(self, 'is_replace_cm3d2_tex', icon='BORDERMOVE')
	
	def execute(self, context):
		data = context.window_manager.clipboard
		lines = data.split('\n')
		
		ob = context.active_object
		me = ob.data
		
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
					
					# tex探し
					if self.is_replace_cm3d2_tex:
						if common.replace_cm3d2_tex(img) and data[0]=='_MainTex':
							for face in me.polygons:
								if face.material_index == ob.active_material_index:
									me.uv_textures.active.data[face.index].image = img
			
			elif type == 'col':
				slot = mate.texture_slots.create(slot_index)
				tex_name = common.line_trim(lines[line_seek+1])
				tex = context.blend_data.textures.new(tex_name, 'BLEND')
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
				tex = context.blend_data.textures.new(tex_name, 'BLEND')
				mate.use_textures[slot_index] = False
				slot.diffuse_color_factor = float(common.line_trim(lines[line_seek+2]))
				slot.texture = tex
				line_seek += 3
			
			else:
				self.report(type={'ERROR'}, message="未知の設定値タイプが見つかりました、中止します")
				return {'CANCELLED'}
			slot_index += 1
		
		common.decorate_material(mate, self.is_decorate, me, ob.active_material_index)
		self.report(type={'INFO'}, message="クリップボードからマテリアルを貼り付けました")
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
				return 'shader1' in mate.keys() and 'shader2' in mate.keys()
		return False
	
	def execute(self, context):
		import re, os.path
		
		mate = context.material
		
		output_text = "1000" + "\n"
		output_text += mate.name.lower() + "\n"
		output_text += mate.name + "\n"
		output_text += mate['shader1'] + "\n"
		output_text += mate['shader2'] + "\n"
		output_text += "\n"
		
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
			output_text += type + "\n"
			output_text += "\t" + common.remove_serial_number(tex.name) + "\n"
			if type == 'tex':
				try:
					img = tex.image
				except:
					self.report(type={'ERROR'}, message="texタイプの設定値の取得に失敗しました、中止します")
					return {'CANCELLED'}
				if img:
					output_text += '\ttex2d' + "\n"
					output_text += "\t" + common.remove_serial_number(img.name) + "\n"
					if 'cm3d2_path' in img.keys():
						path = img['cm3d2_path']
					else:
						path = bpy.path.abspath( bpy.path.abspath(img.filepath) )
					path = path.replace('\\', '/')
					path = re.sub(r'^[\/\.]*', "", path)
					if not re.search(r'^assets/texture/', path, re.I):
						path = "Assets/texture/texture/" + os.path.basename(path)
					output_text += "\t" + path + "\n"
					col = tex_slot.color
					output_text += "\t" + " ".join([str(col[0]), str(col[1]), str(col[2]), str(tex_slot.diffuse_color_factor)]) + "\n"
				else:
					output_text += "\tnull" + "\n"
			elif type == 'col':
				col = tex_slot.color
				output_text += "\t" + " ".join([str(col[0]), str(col[1]), str(col[2]), str(tex_slot.diffuse_color_factor)]) + "\n"
			elif type == 'f':
				output_text += "\t" + str(tex_slot.diffuse_color_factor) + "\n"
		
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="マテリアルテキストをクリップボードにコピーしました")
		return {'FINISHED'}

class decorate_material(bpy.types.Operator):
	bl_idname = 'material.decorate_material'
	bl_label = "マテリアルを装飾"
	bl_description = "スロット内のマテリアルを全て設定に合わせて装飾します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if not ob: return False
		if ob.type != 'MESH': return False
		for slot in ob.material_slots:
			mate = slot.material
			if mate:
				if 'shader1' in mate.keys() and 'shader2' in mate.keys():
					return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		
		for slot_index, slot in enumerate(ob.material_slots):
			mate = slot.material
			if mate:
				if 'shader1' in mate.keys() and 'shader2' in mate.keys():
					common.decorate_material(mate, True, me, slot_index)
		
		return {'FINISHED'}

class quick_texture_show(bpy.types.Operator):
	bl_idname = 'material.quick_texture_show'
	bl_label = "このテクスチャを見る"
	bl_description = "このテクスチャを見る"
	bl_options = {'REGISTER'}
	
	texture_name = bpy.props.StringProperty(name="テクスチャ名")
	
	@classmethod
	def poll(cls, context):
		mate = context.material
		if mate:
			if 'shader1' in mate.keys() and 'shader2' in mate.keys():
				return True
		return False
	
	def execute(self, context):
		mate = context.material
		for index, slot in enumerate(mate.texture_slots):
			if not slot: continue
			if not slot.texture: continue
			if slot.texture.name == self.texture_name:
				mate.active_texture_index = index
				context.space_data.context = 'TEXTURE'
				break
		return {'FINISHED'}
