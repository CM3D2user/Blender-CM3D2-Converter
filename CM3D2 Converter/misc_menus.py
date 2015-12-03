import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# 頂点グループメニューに項目追加
def MESH_MT_vertex_group_specials(self, context):
	self.layout.separator()
	self.layout.operator('object.quick_transfer_vertex_group', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator('object.precision_transfer_vertex_group', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator('object.blur_vertex_group', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator('object.multiply_vertex_group', icon_value=common.preview_collections['main']['KISS'].icon_id)

# 頂点グループパネルに項目追加
def DATA_PT_vertex_groups(self, context):
	import re
	ob = context.active_object
	if ob:
		if len(ob.vertex_groups) and ob.type == 'MESH':
			flag = False
			for vertex_group in ob.vertex_groups:
				if not flag and re.search(r'[_ ]([rRlL])[_ ]', vertex_group.name):
					flag = True
				if not flag and vertex_group.name.count('*') == 1:
					if re.search(r'\.([rRlL])$', vertex_group.name):
						flag = True
				if flag:
					self.layout.label(text="CM3D2用 頂点グループ名変換", icon_value=common.preview_collections['main']['KISS'].icon_id)
					row = self.layout.row(align=True)
					row.operator('object.decode_cm3d2_vertex_group_names', icon='BLENDER', text="CM3D2 → Blender")
					row.operator('object.encode_cm3d2_vertex_group_names', icon_value=common.preview_collections['main']['KISS'].icon_id, text="Blender → CM3D2")
					break

# シェイプメニューに項目追加
def MESH_MT_shape_key_specials(self, context):
	self.layout.separator()
	self.layout.operator('object.quick_shape_key_transfer', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator('object.precision_shape_key_transfer', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator('object.multiply_shape_key', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.separator()
	self.layout.operator('object.blur_shape_key', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator('object.radius_blur_shape_key', icon_value=common.preview_collections['main']['KISS'].icon_id)

# マテリアルタブに項目追加
def MATERIAL_PT_context_material(self, context):
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
			row = box.row()
			row.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			row.operator('material.export_cm3d2_mate', icon='FILE_FOLDER', text="")
			row.operator('material.copy_material', icon='COPYDOWN', text="")
			
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
	import re
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
					row.operator('armature.decode_cm3d2_bone_names', text="CM3D2 → Blender", icon='BLENDER')
					row.operator('armature.encode_cm3d2_bone_names', text="Blender → CM3D2", icon='POSE_DATA')
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
				row.operator('object.copy_armature_bone_data_property', icon='COPYDOWN', text="コピー")
				row.operator('object.paste_armature_bone_data_property', icon='PASTEDOWN', text="貼り付け")
				row.operator('object.remove_armature_bone_data_property', icon='X', text="")

# オブジェクトタブに項目追加
def OBJECT_PT_context_object(self, context):
	import re
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
				row.operator('object.copy_object_bone_data_property', icon='COPYDOWN', text="コピー")
				row.operator('object.paste_object_bone_data_property', icon='PASTEDOWN', text="貼り付け")
				row.operator('object.remove_object_bone_data_property', icon='X', text="")

# モディファイアタブに項目追加
def DATA_PT_modifiers(self, context):
	if 'apply_all_modifier' not in dir(bpy.ops.object):
		ob = context.active_object
		if ob:
			if ob.type == 'MESH':
				me = ob.data
				if me.shape_keys and len(ob.modifiers):
					self.layout.operator('wm.url_open', text="モディファイアを適用できない場合", icon_value=common.preview_collections['main']['KISS'].icon_id).url = "https://sites.google.com/site/matosus304blendernotes/home/download#apply_modifier"

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
		row.operator('text.show_text', icon='ARMATURE_DATA', text="BoneData (%d)" % line_count).name = 'BoneData'
	if 'LocalBoneData' in text_keys:
		txt = bpy.data.texts['LocalBoneData']
		line_count = 0
		for line in txt.as_string().split('\n'):
			if line:
				line_count += 1
		row.operator('text.show_text', icon='BONE_DATA', text="LocalBoneData (%d)" % line_count).name = 'LocalBoneData'
	if 'BoneData' in text_keys and 'LocalBoneData' in text_keys:
		row.operator('text.copy_text_bone_data', icon='COPYDOWN', text="")
		row.operator('text.paste_text_bone_data', icon='PASTEDOWN', text="")
	if 'Material:0' in text_keys:
		self.layout.label(text="", icon='MATERIAL_DATA')
		row = self.layout.row(align=True)
		pass_count = 0
		for i in range(99):
			name = "Material:" + str(i)
			if name in text_keys:
				sub_row = row.row(align=True)
				sub_row.scale_x = 0.5
				sub_row.operator('text.show_text', text=str(i)).name = name
			else:
				pass_count += 1
			if 9 < pass_count:
				break
		if "Material:0" in text_keys:
			row.operator('text.remove_all_material_texts', icon='X', text="")

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
	import os
	
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

# ヘルプメニューに項目追加
def INFO_MT_help(self, context):
	self.layout.separator()
	self.layout.operator('script.update_cm3d2_converter', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.menu('INFO_MT_help_CM3D2_Converter_RSS_sub', icon_value=common.preview_collections['main']['KISS'].icon_id)
	self.layout.operator('wm.show_cm3d2_converter_preference', icon_value=common.preview_collections['main']['KISS'].icon_id)

class INFO_MT_help_CM3D2_Converter_RSS_sub(bpy.types.Menu):
	bl_idname = 'INFO_MT_help_CM3D2_Converter_RSS_sub'
	bl_label = "CM3D2 Converterの更新履歴"
	
	def draw(self, context):
		self.layout.menu('INFO_MT_help_CM3D2_Converter_RSS', text="取得に数秒かかります", icon='FILE_REFRESH')

class INFO_MT_help_CM3D2_Converter_RSS(bpy.types.Menu):
	bl_idname = 'INFO_MT_help_CM3D2_Converter_RSS'
	bl_label = "CM3D2 Converterの更新履歴"
	
	def draw(self, context):
		try:
			import re, urllib, datetime, urllib.request, xml.sax.saxutils
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
				self.layout.operator('wm.url_open', text=text, icon=icon).url = link
				count += 1
		except TypeError:
			self.layout.label(text="更新の取得に失敗しました", icon='ERROR')
