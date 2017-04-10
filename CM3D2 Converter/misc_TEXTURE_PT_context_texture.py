# 「プロパティ」エリア → 「テクスチャ」タブ
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	import os
	
	try:
		tex_slot = context.texture_slot
		tex = context.texture
		mate = context.active_object.active_material
		mate['shader1']
		mate['shader2']
	except: return
	if not tex_slot: return
	
	if tex_slot.use:
		type = 'tex'
	else:
		type = 'col' if tex_slot.use_rgb_to_intensity else 'f'
	base_name = common.remove_serial_number(tex.name)
	
	box = self.layout.box()
	box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
	split = box.split(percentage=0.333333333333333333)
	split.label(text="設定値タイプ:")
	row = split.row()
	
	if type == 'tex': row.label(text='テクスチャ', icon='TEXTURE')
	elif type == 'col': row.label(text='色', icon='COLOR')
	elif type == 'f': row.label(text='値', icon='ARROW_LEFTRIGHT')
	
	check_row = row.row(align=True)
	check_row.prop(tex_slot, 'use', text="")
	sub_row = check_row.row()
	sub_row.prop(tex_slot, 'use_rgb_to_intensity', text="")
	if tex_slot.use:
		sub_row.enabled = False
	box.prop(tex, 'name', icon='SORTALPHA', text="設定値名")
	
	if type == "tex":
		if tex.type == 'IMAGE':
			img = tex.image
			if img:
				if img.source == 'FILE':
					
					if re.search(r"\.[Pp][Nn][Gg]$", img.name):
						img.name = re.sub(r"\.[Pp][Nn][Gg]$", "", img.name)
					if re.search(r"\.[Pp][Nn][Gg]\.\d{3}$", img.name):
						img.name = re.sub(r"\.[Pp][Nn][Gg](\.\d{3})$", r"\1", img.name)
					
					sub_box = box.box()
					row = sub_box.split(percentage=0.333333333333, align=True)
					row.label(text="テクスチャ名:")
					row.template_ID(tex, 'image', open='image.open')
					if 'cm3d2_path' not in img:
						img['cm3d2_path'] = "Assets\\texture\\texture\\" + os.path.basename(img.filepath)
					sub_box.prop(img, '["cm3d2_path"]', text="テクスチャパス")
					
					if base_name == "_ToonRamp":
						sub_box.menu('TEXTURE_PT_context_texture_ToonRamp', icon='NLA')
					elif base_name == "_ShadowRateToon":
						sub_box.menu('TEXTURE_PT_context_texture_ShadowRateToon', icon='NLA')
					split = sub_box.split(percentage=0.333333333333, align=True)
					split.label(text="オフセット:")
					row = split.row(align=True)
					row.prop(tex_slot, 'color', index=0, text="")
					row.prop(tex_slot, 'color', index=1, text="")
					
					split = sub_box.split(percentage=0.333333333333, align=True)
					split.label(text="拡大/縮小:")
					row = split.row(align=True)
					row.prop(tex_slot, 'color', index=2, text="")
					row.prop(tex_slot, 'diffuse_color_factor', text="")
					
					row = sub_box.row()
					row.operator('image.show_image', text="画像を表示", icon='ZOOM_IN').image_name = img.name
					if len(img.pixels):
						row.operator('image.quick_export_cm3d2_tex', text="texで保存", icon='FILESEL')
					else:
						row.operator('image.replace_cm3d2_tex', icon='BORDERMOVE')
	
	elif type == "col":
		sub_box = box.box()
		
		#row = sub_box.split(percentage=0.7, align=True)
		row = sub_box.row(align=True)
		row.prop(tex_slot, 'color', text="")
		row.operator('texture.auto_set_color_value', icon='RECOVER_AUTO', text="自動設定")
		row.operator('texture.set_color_value', text="", icon='MATCAP_10').color = [0, 0, 0] + [tex_slot.diffuse_color_factor]
		row.operator('texture.set_color_value', text="", icon='MATCAP_24').color = [1, 1, 1] + [tex_slot.diffuse_color_factor]
		
		row = sub_box.row(align=True)
		row.operator('texture.set_color_value', text="", icon='TRIA_LEFT').color = list(tex_slot.color) + [0]
		row.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
		row.operator('texture.set_color_value', text="", icon='TRIA_RIGHT').color = list(tex_slot.color) + [1]
	
	elif type == "f":
		sub_box = box.box()
		row = sub_box.row(align=True)
		row.prop(tex_slot, 'diffuse_color_factor', icon='ARROW_LEFTRIGHT', text="値")
		
		data_path = 'texture_slot.diffuse_color_factor'
		if base_name == '_Shininess':
			row.menu('TEXTURE_PT_context_texture_values_normal', icon='DOWNARROW_HLT', text="")
			
			row = sub_box.row(align=True)
			row.operator('texture.set_color_value', text="0.0", icon='MATCAP_10').color = list(tex_slot.color) + [0.0]
			row.operator('texture.set_color_value', text="0.25").color = list(tex_slot.color) + [0.25]
			row.operator('texture.set_color_value', text="0.5").color = list(tex_slot.color) + [0.5]
			row.operator('texture.set_color_value', text="0.75").color = list(tex_slot.color) + [0.75]
			row.operator('texture.set_color_value', text="1.0", icon='MATCAP_09').color = list(tex_slot.color) + [1.0]
		
		elif base_name == '_OutlineWidth':
			row.menu('TEXTURE_PT_context_texture_values_OutlineWidth', icon='DOWNARROW_HLT', text="")
			
			row = sub_box.row(align=True)
			row.operator('texture.set_color_value', text="0.001", icon='MATSPHERE').color = list(tex_slot.color) + [0.001]
			row.operator('texture.set_color_value', text="0.0015").color = list(tex_slot.color) + [0.0015]
			row.operator('texture.set_color_value', text="0.002", icon='ANTIALIASED').color = list(tex_slot.color) + [0.002]
			
			split = sub_box.split(percentage=0.3)
			split.label(text="正確な値: ")
			split.label(text=str(tex_slot.diffuse_color_factor))
		
		elif base_name == '_RimPower':
			row.menu('TEXTURE_PT_context_texture_values_RimPower', icon='DOWNARROW_HLT', text="")
			
			row = sub_box.row(align=True)
			row.operator('texture.set_color_value', text="1", icon='BRUSH_TEXFILL').color = list(tex_slot.color) + [1]
			row.operator('texture.set_color_value', text="10").color = list(tex_slot.color) + [10]
			row.operator('texture.set_color_value', text="20").color = list(tex_slot.color) + [20]
			row.operator('texture.set_color_value', text="30", icon='MATCAP_07').color = list(tex_slot.color) + [30]
		
		elif base_name == '_RimShift':
			row.menu('TEXTURE_PT_context_texture_values_normal', icon='DOWNARROW_HLT', text="")
			
			row = sub_box.row(align=True)
			row.operator('texture.set_color_value', text="0.0", icon='FULLSCREEN_EXIT').color = list(tex_slot.color) + [0.0]
			row.operator('texture.set_color_value', text="0.25").color = list(tex_slot.color) + [0.25]
			row.operator('texture.set_color_value', text="0.5").color = list(tex_slot.color) + [0.5]
			row.operator('texture.set_color_value', text="0.75").color = list(tex_slot.color) + [0.75]
			row.operator('texture.set_color_value', text="1.0", icon='FULLSCREEN_ENTER').color = list(tex_slot.color) + [1.0]
	
	box.operator('texture.sync_tex_color_ramps', icon='LINKED')
	
	description = ""
	if base_name == '_MainTex':
		description = ["面の色を決定するテクスチャを指定。", "普段テスクチャと呼んでいるものは基本コレです。", "テクスチャパスは適当でも動きます。", "しかし、テクスチャ名はきちんと決めましょう。"]
	if base_name == '_ToonRamp':
		description = ["暗い部分に乗算するグラデーション画像を指定します。"]
	elif base_name == '_ShadowTex':
		description = ["陰部分の面の色を決定するテクスチャを指定。", "「_ShadowRateToon」で範囲を指定します。"]
	if base_name == '_ShadowRateToon':
		description = ["「_ShadowTex」を有効にする部分を指定します。", "黒色で有効、白色で無効。"]
	elif base_name == '_Color':
		description = ["面の色を指定。", "白色で無効。基本的に白色で良いでしょう。"]
	elif base_name == '_ShadowColor':
		description = ["影の色を指定。白色で無効。", "別の物体に遮られてできた「影」の色です。"]
	elif base_name == '_RimColor':
		description = ["リムライトの色を指定。", "リムライトとは縁にできる光の反射のことです。"]
	elif base_name == '_OutlineColor':
		description = ["輪郭線の色を指定。", "黒にするか、テクスチャの明度を", "落としたものを指定するとより良いでしょう。"]
	elif base_name == '_Shininess':
		description = ["スペキュラーの強さを指定。0.0～1.0で指定。", "スペキュラーとは面の角度と光源の角度によって", "できるハイライトのことです。", "金属、皮、ガラスなどに使うと良いでしょう。"]
	elif base_name == '_OutlineWidth':
		description = ["輪郭線の太さを指定。", "0.002は太め、0.001は細め。"]
	elif base_name == '_RimPower':
		description = ["リムライトの強さを指定。", "この値は10以上なことも多いです。", "0に近い値だと正常に表示されません。"]
	elif base_name == '_RimShift':
		description = ["リムライトの幅を指定。", "0.0～1.0で指定。0.5でもかなり強い。"]
	elif base_name == '_RenderTex':
		description = ["モザイクシェーダーにある設定値。", "特に設定の必要なし。"]
	elif base_name == '_FloatValue1':
		description = ["モザイクの大きさ？(未確認)"]
	
	if description != "":
		sub_box = box.box()
		col = sub_box.column(align=True)
		col.label(text="解説", icon='TEXT')
		for line in description:
			col.label(text=line)

# _ToonRamp設定メニュー
class TEXTURE_PT_context_texture_ToonRamp(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_ToonRamp'
	bl_label = "_ToonRamp 設定"
	
	def draw(self, context):
		l = self.layout
		cmd = 'texture.set_default_toon_textures'
		l.operator(cmd, text="NoTex", icon='SPACE2').name = "NoTex"
		l.operator(cmd, text="ToonBlackA1", icon='SPACE2').name = "ToonBlackA1"
		l.operator(cmd, text="ToonBlueA1", icon='SPACE2').name = "ToonBlueA1"
		l.operator(cmd, text="ToonBlueA2", icon='SPACE2').name = "ToonBlueA2"
		l.operator(cmd, text="ToonBrownA1", icon='SPACE2').name = "ToonBrownA1"
		l.operator(cmd, text="ToonDress_Shadow", icon='LAYER_USED').name = "ToonDress_Shadow"
		l.operator(cmd, text="ToonFace", icon='SPACE2').name = "ToonFace"
		l.operator(cmd, text="ToonFace_Shadow", icon='LAYER_USED').name = "ToonFace_Shadow"
		l.operator(cmd, text="ToonFace002", icon='SPACE2').name = "ToonFace002"
		l.operator(cmd, text="ToonGrayA1", icon='SPACE2').name = "ToonGrayA1"
		l.operator(cmd, text="ToonGreenA1", icon='SPACE2').name = "ToonGreenA1"
		l.operator(cmd, text="ToonGreenA2", icon='SPACE2').name = "ToonGreenA2"
		l.operator(cmd, text="ToonOrangeA1", icon='SPACE2').name = "ToonOrangeA1"
		l.operator(cmd, text="ToonPinkA1", icon='SPACE2').name = "ToonPinkA1"
		l.operator(cmd, text="ToonPinkA2", icon='SPACE2').name = "ToonPinkA2"
		l.operator(cmd, text="ToonPurpleA1", icon='SPACE2').name = "ToonPurpleA1"
		l.operator(cmd, text="ToonRedA1", icon='SPACE2').name = "ToonRedA1"
		l.operator(cmd, text="ToonRedA2", icon='SPACE2').name = "ToonRedA2"
		l.operator(cmd, text="ToonSkin", icon='SPACE2').name = "ToonSkin"
		l.operator(cmd, text="ToonSkin_Shadow", icon='LAYER_USED').name = "ToonSkin_Shadow"
		l.operator(cmd, text="ToonSkin002", icon='SPACE2').name = "ToonSkin002"
		l.operator(cmd, text="ToonYellowA1", icon='SPACE2').name = "ToonYellowA1"
		l.operator(cmd, text="ToonYellowA2", icon='SPACE2').name = "ToonYellowA2"
		l.operator(cmd, text="ToonYellowA3", icon='SPACE2').name = "ToonYellowA3"

# _ShadowRateToon設定メニュー
class TEXTURE_PT_context_texture_ShadowRateToon(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_ShadowRateToon'
	bl_label = "_ShadowRateToon 設定"
	
	def draw(self, context):
		l = self.layout
		cmd = 'texture.set_default_toon_textures'
		l.operator(cmd, text="NoTex", icon='LAYER_USED').name = "NoTex"
		l.operator(cmd, text="ToonBlackA1", icon='LAYER_USED').name = "ToonBlackA1"
		l.operator(cmd, text="ToonBlueA1", icon='LAYER_USED').name = "ToonBlueA1"
		l.operator(cmd, text="ToonBlueA2", icon='LAYER_USED').name = "ToonBlueA2"
		l.operator(cmd, text="ToonBrownA1", icon='LAYER_USED').name = "ToonBrownA1"
		l.operator(cmd, text="ToonDress_Shadow", icon='SPACE2').name = "ToonDress_Shadow"
		l.operator(cmd, text="ToonFace", icon='LAYER_USED').name = "ToonFace"
		l.operator(cmd, text="ToonFace_Shadow", icon='SPACE2').name = "ToonFace_Shadow"
		l.operator(cmd, text="ToonFace002", icon='LAYER_USED').name = "ToonFace002"
		l.operator(cmd, text="ToonGrayA1", icon='LAYER_USED').name = "ToonGrayA1"
		l.operator(cmd, text="ToonGreenA1", icon='LAYER_USED').name = "ToonGreenA1"
		l.operator(cmd, text="ToonGreenA2", icon='LAYER_USED').name = "ToonGreenA2"
		l.operator(cmd, text="ToonOrangeA1", icon='LAYER_USED').name = "ToonOrangeA1"
		l.operator(cmd, text="ToonPinkA1", icon='LAYER_USED').name = "ToonPinkA1"
		l.operator(cmd, text="ToonPinkA2", icon='LAYER_USED').name = "ToonPinkA2"
		l.operator(cmd, text="ToonPurpleA1", icon='LAYER_USED').name = "ToonPurpleA1"
		l.operator(cmd, text="ToonRedA1", icon='LAYER_USED').name = "ToonRedA1"
		l.operator(cmd, text="ToonRedA2", icon='LAYER_USED').name = "ToonRedA2"
		l.operator(cmd, text="ToonSkin", icon='LAYER_USED').name = "ToonSkin"
		l.operator(cmd, text="ToonSkin_Shadow", icon='SPACE2').name = "ToonSkin_Shadow"
		l.operator(cmd, text="ToonSkin002", icon='LAYER_USED').name = "ToonSkin002"
		l.operator(cmd, text="ToonYellowA1", icon='LAYER_USED').name = "ToonYellowA1"
		l.operator(cmd, text="ToonYellowA2", icon='LAYER_USED').name = "ToonYellowA2"
		l.operator(cmd, text="ToonYellowA3", icon='LAYER_USED').name = "ToonYellowA3"

# 0.0～1.0までの値設定メニュー
class TEXTURE_PT_context_texture_values_normal(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_values_normal'
	bl_label = "値リスト"
	
	def draw(self, context):
		tex_slot = context.texture_slot
		for i in range(11):
			value = round(i * 0.1, 1)
			icon = 'LAYER_USED' if i % 2 else 'LAYER_ACTIVE'
			self.layout.operator('texture.set_color_value', text=str(value), icon=icon).color = list(tex_slot.color) + [value]

# _OutlineWidth用の値設定メニュー
class TEXTURE_PT_context_texture_values_OutlineWidth(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_values_OutlineWidth'
	bl_label = "値リスト"
	
	def draw(self, context):
		tex_slot = context.texture_slot
		for i in range(16):
			value = round(i * 0.0002, 4)
			icon = 'LAYER_USED' if i % 2 else 'LAYER_ACTIVE'
			self.layout.operator('texture.set_color_value', text=str(value), icon=icon).color = list(tex_slot.color) + [value]

# _RimPower用の値設定メニュー
class TEXTURE_PT_context_texture_values_RimPower(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_values_RimPower'
	bl_label = "値リスト"
	
	def draw(self, context):
		tex_slot = context.texture_slot
		for i in range(16):
			value = round(i * 2, 0)
			icon = 'LAYER_USED' if i % 2 else 'LAYER_ACTIVE'
			if value == 0:
				icon = 'ERROR'
			self.layout.operator('texture.set_color_value', text=str(value), icon=icon).color = list(tex_slot.color) + [value]

class show_image(bpy.types.Operator):
	bl_idname = 'image.show_image'
	bl_label = "画像を表示"
	bl_description = "指定の画像をUV/画像エディターに表示します"
	bl_options = {'REGISTER', 'UNDO'}
	
	image_name = bpy.props.StringProperty(name="画像名")
	
	def execute(self, context):
		if self.image_name in context.blend_data.images:
			img = context.blend_data.images[self.image_name]
		else:
			self.report(type={'ERROR'}, message="指定された画像が見つかりません")
			return {'CANCELLED'}
		
		area = common.get_request_area(context, 'IMAGE_EDITOR')
		if area:
			common.set_area_space_attr(area, 'image', img)
		else:
			self.report(type={'ERROR'}, message="画像を表示できるエリアが見つかりませんでした")
			return {'CANCELLED'}
		return {'FINISHED'}

class replace_cm3d2_tex(bpy.types.Operator):
	bl_idname = 'image.replace_cm3d2_tex'
	bl_label = "テクスチャを探す"
	bl_description = "CM3D2本体のインストールフォルダからtexファイルを探して開きます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'texture' in dir(context):
			tex = context.texture
			return 'image' in dir(tex)
		return False
	
	def execute(self, context):
		tex = context.texture
		img = tex.image
		if not common.replace_cm3d2_tex(img):
			self.report(type={'ERROR'}, message="見つかりませんでした")
			return {'CANCELLED'}
		tex.image_user.use_auto_refresh = True
		return {'FINISHED'}

class sync_tex_color_ramps(bpy.types.Operator):
	bl_idname = 'texture.sync_tex_color_ramps'
	bl_label = "設定をプレビューに同期"
	bl_description = "設定値をテクスチャのプレビューに適用してわかりやすくします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'material' in dir(context):
			if context.material:
				return True
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			return context.texture_slot and context.texture
		return False
	
	def execute(self, context):
		for mate in context.blend_data.materials:
			if 'shader1' in mate and 'shader2' in mate:
				for slot in mate.texture_slots:
					if not slot:
						continue
					common.set_texture_color(slot)
		return {'FINISHED'}

class set_default_toon_textures(bpy.types.Operator):
	bl_idname = 'texture.set_default_toon_textures'
	bl_label = "トゥーンを選択"
	bl_description = "CM3D2にデフォルトで入っているトゥーンテクスチャを選択できます"
	bl_options = {'REGISTER', 'UNDO'}
	
	name = bpy.props.StringProperty(name="テクスチャ名")
	#dir = bpy.props.StringProperty(name="パス", default="Assets\\texture\\texture\\toon\\")
	
	@classmethod
	def poll(cls, context):
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			if context.texture_slot and context.texture:
				name = common.remove_serial_number(context.texture.name)
				return name == "_ToonRamp" or name == "_ShadowRateToon"
		return False
	
	def execute(self, context):
		import os.path, struct
		img = context.texture.image
		img.name = self.name
		
		png_path = os.path.join( os.path.dirname(bpy.path.abspath(img.filepath)), self.name + ".png" )
		tex_path = os.path.splitext(png_path)[0] + ".tex"
		if not os.path.exists(png_path):
			if os.path.exists(tex_path):
				tex_file = open(tex_path, 'rb')
				header_ext = common.read_str(tex_file)
				if header_ext == 'CM3D2_TEX':
					tex_file.seek(4, 1)
					common.read_str(tex_file)
					png_size = struct.unpack('<i', tex_file.read(4))[0]
					png_file = open(png_path, 'wb')
					png_file.write(tex_file.read(png_size))
					png_file.close()
				tex_file.close()
		img.filepath = png_path
		img.reload()
		
		img['cm3d2_path'] = bpy.path.abspath(img.filepath)
		return {'FINISHED'}

class auto_set_color_value(bpy.types.Operator):
	bl_idname = 'texture.auto_set_color_value'
	bl_label = "色設定値を自動設定"
	bl_description = "色関係の設定値をテクスチャの色情報から自動で設定します"
	bl_options = {'REGISTER', 'UNDO'}
	
	is_all = bpy.props.BoolProperty(name="全てが対象", default=True)
	saturation_multi = bpy.props.FloatProperty(name="彩度の乗算値", default=2.2, min=0, max=5, soft_min=0, soft_max=5, step=10, precision=2)
	value_multi = bpy.props.FloatProperty(name="明度の乗算値", default=0.3, min=0, max=5, soft_min=0, soft_max=5, step=10, precision=2)
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if not ob: return False
		if ob.type != 'MESH': return False
		me = ob.data
		mate = ob.active_material
		if not mate: return False
		for slot in mate.texture_slots:
			if not slot: continue
			tex = slot.texture
			name = common.remove_serial_number(tex.name)
			if name == '_MainTex':
				img = tex.image
				if img:
					if len(img.pixels):
						break
				if me.uv_textures.active:
					if me.uv_textures.active.data[0].image:
						if len(me.uv_textures.active.data[0].image.pixels):
							break
		else: return False
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			slot = context.texture_slot
			tex = context.texture
			name = common.remove_serial_number(tex.name)
			if name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.prop(self, 'is_all', icon='ACTION')
		row = self.layout.row()
		row.label(text="", icon='SMOOTH')
		row.prop(self, 'saturation_multi')
		row = self.layout.row()
		row.label(text="", icon='SOLID')
		row.prop(self, 'value_multi')
	
	def execute(self, context):
		ob = context.active_object
		me = ob.data
		mate = ob.active_material
		active_slot = context.texture_slot
		active_tex = context.texture
		tex_name = common.remove_serial_number(active_tex.name)
		
		target_slots = []
		if self.is_all:
			for slot in mate.texture_slots:
				if not slot: continue
				name = common.remove_serial_number(slot.texture.name)
				if name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
					target_slots.append(slot)
		else:
			target_slots.append(active_slot)
		
		for slot in mate.texture_slots:
			if not slot: continue
			name = common.remove_serial_number(slot.texture.name)
			if name == '_MainTex':
				img = slot.texture.image
				if img:
					if len(img.pixels):
						break
		else:
			img = me.uv_textures.active.data[0].image
		
		sample_count = 10
		img_width, img_height, img_channel = img.size[0], img.size[1], img.channels
		
		bm = bmesh.new()
		bm.from_mesh(me)
		uv_lay = bm.loops.layers.uv.active
		uvs = [l[uv_lay].uv[:] for f in bm.faces if f.material_index == ob.active_material_index for l in f.loops]
		bm.free()
		
		average_color = mathutils.Color([0, 0, 0])
		seek_interval = len(uvs) / sample_count
		for sample_index in range(sample_count):
			
			uv_index = int(seek_interval * sample_index)
			x, y = uvs[uv_index]
			x, y = int(x * img_width), int(y * img_height)
			
			pixel_index = ((y * img_width) + x) * img_channel
			color = mathutils.Color(img.pixels[pixel_index:pixel_index+3])
			
			average_color += color
		average_color /= sample_count
		average_color.s *= self.saturation_multi
		average_color.v *= self.value_multi
		
		for slot in target_slots:
			slot.color = average_color[:3]
			common.set_texture_color(slot)
		
		return {'FINISHED'}

class quick_export_cm3d2_tex(bpy.types.Operator):
	bl_idname = 'image.quick_export_cm3d2_tex'
	bl_label = "texで保存"
	bl_description = "テクスチャの画像を同フォルダにtexとして保存します"
	bl_options = {'REGISTER'}
	
	def execute(self, context):
		import os.path
		
		try:
			slot = context.texture_slot
			tex = context.texture
			img = tex.image
			img.pixels[0]
		except:
			self.report(type={'ERROR'}, message="失敗しました")
			return {'CANCELLED'}
		
		override = context.copy()
		override['edit_image'] = img
		filepath = os.path.splitext( bpy.path.abspath(img.filepath) )[0] + ".tex"
		path = "assets/texture/texture/" + os.path.basename( bpy.path.abspath(img.filepath) )
		if 'cm3d2_path' in img:
			path = img['cm3d2_path']
		if os.path.exists(filepath):
			file = open(filepath, 'rb')
			header_ext = common.read_str(file)
			if header_ext == 'CM3D2_TEX':
				file.seek(4, 1)
				path = common.read_str(file)
			file.close()
		bpy.ops.image.export_cm3d2_tex(override, filepath=filepath, path=path)
		
		self.report(type={'INFO'}, message="同フォルダにtexとして保存しました")
		return {'FINISHED'}

class set_color_value(bpy.types.Operator):
	bl_idname = 'texture.set_color_value'
	bl_label = "色設定値を設定"
	bl_description = "色タイプの設定値を設定します"
	bl_options = {'REGISTER', 'UNDO'}
	
	color = bpy.props.FloatVectorProperty(name="色", default=(0, 0, 0, 0), subtype='COLOR', size=4)
	
	@classmethod
	def poll(cls, context):
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			if context.texture_slot and context.texture:
				return True
		return False
	
	def execute(self, context):
		slot = context.texture_slot
		slot.color = self.color[:3]
		slot.diffuse_color_factor = self.color[3]
		common.set_texture_color(slot)
		return {'FINISHED'}
