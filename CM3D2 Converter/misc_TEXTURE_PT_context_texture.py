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
	split = box.split(percentage=0.3)
	split.label(text="設定値タイプ:")
	row = split.row(align=True)
	
	if type == 'tex': row.label(text='テクスチャ')
	elif type == 'col': row.label(text='色')
	elif type == 'f': row.label(text='値')
	
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
					
					if base_name == "_MainTex":
						sub_box.operator('texture.auto_set_color_value', icon='RECOVER_AUTO')
					
					if base_name == "_ToonRamp":
						sub_box.menu('TEXTURE_PT_context_texture_ToonRamp', icon='COLOR')
					elif base_name == "_ShadowRateToon":
						sub_box.menu('TEXTURE_PT_context_texture_ShadowRateToon', icon='COLOR')
					
					if len(img.pixels):
						sub_box.operator('image.show_image', text="この画像を表示", icon='ZOOM_IN').image_name = img.name
					else:
						sub_box.operator('image.replace_cm3d2_tex', icon='BORDERMOVE')
				#box.prop(tex_slot, 'color', text="")
				#box.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
	elif type == "col":
		sub_box = box.box()
		sub_box.prop(tex_slot, 'color', text="")
		sub_box.prop(tex_slot, 'diffuse_color_factor', icon='IMAGE_RGB_ALPHA', text="色の透明度", slider=True)
		if base_name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
			sub_box.operator('texture.auto_set_color_value', icon='RECOVER_AUTO')
		sub_box.operator('texture.sync_tex_color_ramps', icon='COLOR')
	elif type == "f":
		sub_box = box.box()
		sub_box.prop(tex_slot, 'diffuse_color_factor', icon='ARROW_LEFTRIGHT', text="値")
		split = sub_box.split(percentage=0.3)
		split.label(text="正確な値: ")
		split.label(text=str(tex_slot.diffuse_color_factor))
		sub_box.operator('texture.sync_tex_color_ramps', icon='COLOR')
	
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

# _ToonRamp設定メニュー
class TEXTURE_PT_context_texture_ToonRamp(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_ToonRamp'
	bl_label = "_ToonRamp 設定"
	
	def draw(self, context):
		l = self.layout
		l.operator('texture.set_default_toon_textures', text="NoTex", icon='SPACE2').name = "NoTex"
		l.operator('texture.set_default_toon_textures', text="ToonBlackA1", icon='SPACE2').name = "ToonBlackA1"
		l.operator('texture.set_default_toon_textures', text="ToonBlueA1", icon='SPACE2').name = "ToonBlueA1"
		l.operator('texture.set_default_toon_textures', text="ToonBlueA2", icon='SPACE2').name = "ToonBlueA2"
		l.operator('texture.set_default_toon_textures', text="ToonBrownA1", icon='SPACE2').name = "ToonBrownA1"
		l.operator('texture.set_default_toon_textures', text="ToonDress_Shadow", icon='LAYER_USED').name = "ToonDress_Shadow"
		l.operator('texture.set_default_toon_textures', text="ToonFace", icon='SPACE2').name = "ToonFace"
		l.operator('texture.set_default_toon_textures', text="ToonFace_Shadow", icon='LAYER_USED').name = "ToonFace_Shadow"
		l.operator('texture.set_default_toon_textures', text="ToonFace002", icon='SPACE2').name = "ToonFace002"
		l.operator('texture.set_default_toon_textures', text="ToonGrayA1", icon='SPACE2').name = "ToonGrayA1"
		l.operator('texture.set_default_toon_textures', text="ToonGreenA1", icon='SPACE2').name = "ToonGreenA1"
		l.operator('texture.set_default_toon_textures', text="ToonGreenA2", icon='SPACE2').name = "ToonGreenA2"
		l.operator('texture.set_default_toon_textures', text="ToonOrangeA1", icon='SPACE2').name = "ToonOrangeA1"
		l.operator('texture.set_default_toon_textures', text="ToonPinkA1", icon='SPACE2').name = "ToonPinkA1"
		l.operator('texture.set_default_toon_textures', text="ToonPinkA2", icon='SPACE2').name = "ToonPinkA2"
		l.operator('texture.set_default_toon_textures', text="ToonPurpleA1", icon='SPACE2').name = "ToonPurpleA1"
		l.operator('texture.set_default_toon_textures', text="ToonRedA1", icon='SPACE2').name = "ToonRedA1"
		l.operator('texture.set_default_toon_textures', text="ToonRedA2", icon='SPACE2').name = "ToonRedA2"
		l.operator('texture.set_default_toon_textures', text="ToonSkin", icon='SPACE2').name = "ToonSkin"
		l.operator('texture.set_default_toon_textures', text="ToonSkin_Shadow", icon='LAYER_USED').name = "ToonSkin_Shadow"
		l.operator('texture.set_default_toon_textures', text="ToonSkin002", icon='SPACE2').name = "ToonSkin002"
		l.operator('texture.set_default_toon_textures', text="ToonYellowA1", icon='SPACE2').name = "ToonYellowA1"
		l.operator('texture.set_default_toon_textures', text="ToonYellowA2", icon='SPACE2').name = "ToonYellowA2"
		l.operator('texture.set_default_toon_textures', text="ToonYellowA3", icon='SPACE2').name = "ToonYellowA3"

# _ShadowRateToon設定メニュー
class TEXTURE_PT_context_texture_ShadowRateToon(bpy.types.Menu):
	bl_idname = 'TEXTURE_PT_context_texture_ShadowRateToon'
	bl_label = "_ShadowRateToon 設定"
	
	def draw(self, context):
		l = self.layout
		l.operator('texture.set_default_toon_textures', text="NoTex", icon='LAYER_USED').name = "NoTex"
		l.operator('texture.set_default_toon_textures', text="ToonBlackA1", icon='LAYER_USED').name = "ToonBlackA1"
		l.operator('texture.set_default_toon_textures', text="ToonBlueA1", icon='LAYER_USED').name = "ToonBlueA1"
		l.operator('texture.set_default_toon_textures', text="ToonBlueA2", icon='LAYER_USED').name = "ToonBlueA2"
		l.operator('texture.set_default_toon_textures', text="ToonBrownA1", icon='LAYER_USED').name = "ToonBrownA1"
		l.operator('texture.set_default_toon_textures', text="ToonDress_Shadow", icon='SPACE2').name = "ToonDress_Shadow"
		l.operator('texture.set_default_toon_textures', text="ToonFace", icon='LAYER_USED').name = "ToonFace"
		l.operator('texture.set_default_toon_textures', text="ToonFace_Shadow", icon='SPACE2').name = "ToonFace_Shadow"
		l.operator('texture.set_default_toon_textures', text="ToonFace002", icon='LAYER_USED').name = "ToonFace002"
		l.operator('texture.set_default_toon_textures', text="ToonGrayA1", icon='LAYER_USED').name = "ToonGrayA1"
		l.operator('texture.set_default_toon_textures', text="ToonGreenA1", icon='LAYER_USED').name = "ToonGreenA1"
		l.operator('texture.set_default_toon_textures', text="ToonGreenA2", icon='LAYER_USED').name = "ToonGreenA2"
		l.operator('texture.set_default_toon_textures', text="ToonOrangeA1", icon='LAYER_USED').name = "ToonOrangeA1"
		l.operator('texture.set_default_toon_textures', text="ToonPinkA1", icon='LAYER_USED').name = "ToonPinkA1"
		l.operator('texture.set_default_toon_textures', text="ToonPinkA2", icon='LAYER_USED').name = "ToonPinkA2"
		l.operator('texture.set_default_toon_textures', text="ToonPurpleA1", icon='LAYER_USED').name = "ToonPurpleA1"
		l.operator('texture.set_default_toon_textures', text="ToonRedA1", icon='LAYER_USED').name = "ToonRedA1"
		l.operator('texture.set_default_toon_textures', text="ToonRedA2", icon='LAYER_USED').name = "ToonRedA2"
		l.operator('texture.set_default_toon_textures', text="ToonSkin", icon='LAYER_USED').name = "ToonSkin"
		l.operator('texture.set_default_toon_textures', text="ToonSkin_Shadow", icon='SPACE2').name = "ToonSkin_Shadow"
		l.operator('texture.set_default_toon_textures', text="ToonSkin002", icon='LAYER_USED').name = "ToonSkin002"
		l.operator('texture.set_default_toon_textures', text="ToonYellowA1", icon='LAYER_USED').name = "ToonYellowA1"
		l.operator('texture.set_default_toon_textures', text="ToonYellowA2", icon='LAYER_USED').name = "ToonYellowA2"
		l.operator('texture.set_default_toon_textures', text="ToonYellowA3", icon='LAYER_USED').name = "ToonYellowA3"

class show_image(bpy.types.Operator):
	bl_idname = 'image.show_image'
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
		return {'FINISHED'}

class sync_tex_color_ramps(bpy.types.Operator):
	bl_idname = 'texture.sync_tex_color_ramps'
	bl_label = "設定をテクスチャの色に同期"
	bl_description = "この設定値をテクスチャの色に適用してわかりやすくします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			return context.texture_slot and context.texture
		return False
	
	def execute(self, context):
		for mate in context.blend_data.materials:
			if 'shader1' in mate.keys() and 'shader2' in mate.keys():
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
	dir = bpy.props.StringProperty(name="パス", default="Assets\\texture\\texture\\toon\\")
	
	@classmethod
	def poll(cls, context):
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			if context.texture_slot and context.texture:
				name = common.remove_serial_number(context.texture.name)
				return name == "_ToonRamp" or name == "_ShadowRateToon"
		return False
	
	def execute(self, context):
		img = context.texture.image
		img.name = self.name
		img.filepath = self.dir + self.name + ".png"
		img['cm3d2_path'] = img.filepath
		return {'FINISHED'}

class auto_set_color_value(bpy.types.Operator):
	bl_idname = 'texture.auto_set_color_value'
	bl_label = "色設定値を自動設定"
	bl_description = "色関係の設定値をテクスチャの色情報から自動で設定します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if not ob: return False
		if ob.type != 'MESH': return False
		mate = ob.active_material
		if not mate: return False
		for slot in mate.texture_slots:
			if not slot: continue
			tex = slot.texture
			name = common.remove_serial_number(tex.name)
			if name == '_MainTex':
				img = tex.image
				if not img: return False
				if not len(img.pixels): return False
				break
		else: return False
		if 'texture_slot' in dir(context) and 'texture' in dir(context):
			slot = context.texture_slot
			tex = context.texture
			name = common.remove_serial_number(tex.name)
			
			if name == '_MainTex':
				for slot in mate.texture_slots:
					if not slot: continue
					tex = slot.texture
					name = common.remove_serial_number(tex.name)
					if name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
						return True
				return False
			elif name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
				return True
		return False
	
	def execute(self, context):
		import numpy
		
		ob = context.active_object
		me = ob.data
		mate = ob.active_material
		active_slot = context.texture_slot
		active_tex = context.texture
		tex_name = common.remove_serial_number(active_tex.name)
		
		target_slots = []
		if tex_name == '_MainTex':
			for slot in mate.texture_slots:
				if not slot: continue
				name = common.remove_serial_number(slot.texture.name)
				if name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
					target_slots.append(slot)
			img = active_tex.image
		elif tex_name in ['_ShadowColor', '_RimColor', '_OutlineColor']:
			target_slots.append(active_slot)
			for slot in mate.texture_slots:
				if not slot: continue
				name = common.remove_serial_number(slot.texture.name)
				if name == '_MainTex':
					img = slot.texture.image
					break
		
		sample_count = 10
		img_width, img_height, img_channel = img.size[0], img.size[1], img.channels
		pixels = numpy.array(img.pixels).reshape(img_height, img_width, img_channel)
		
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
			
			color = mathutils.Color(pixels[y, x, :3])
			average_color += color
		average_color /= sample_count
		average_color.s *= 2.2
		average_color.v *= 0.3
		
		for slot in target_slots:
			slot.color = average_color[:3]
			common.set_texture_color(slot)
		
		return {'FINISHED'}
