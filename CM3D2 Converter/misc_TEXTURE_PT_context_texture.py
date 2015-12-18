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
		sub_box.operator('texture.sync_tex_color_ramps', icon='COLOR')
	elif type == "f":
		sub_box = box.box()
		sub_box.prop(tex_slot, 'diffuse_color_factor', icon='ARROW_LEFTRIGHT', text="値")
		split = sub_box.split(percentage=0.3)
		split.label(text="正確な値: ")
		split.label(text=str(tex_slot.diffuse_color_factor))
		sub_box.operator('texture.sync_tex_color_ramps', icon='COLOR')
	
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
