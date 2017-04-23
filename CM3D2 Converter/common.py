import bpy, os, re, math, bmesh, struct, shutil, mathutils
from . import fileutil

# アドオン情報
bl_info = {
	"name" : "CM3D2 Converter",
	"author" : "",
	"version" : (20170423, 991004),
	"blender" : (2, 76, 0),
	"location" : "ファイル > インポート/エクスポート > CM3D2 Model (.model)",
	"description" : "カスタムメイド3D2の専用ファイルのインポート/エクスポートを行います",
	"warning" : "",
	"wiki_url" : "https://github.com/CM3Duser/Blender-CM3D2-Converter",
	"tracker_url" : "http://jbbs.shitaraba.net/bbs/subject.cgi/game/55179/?q=%A1%D6%A5%AB%A5%B9%A5%BF%A5%E0%A5%E1%A5%A4%A5%C93D2%A1%D7%B2%FE%C2%A4%A5%B9%A5%EC%A5%C3%A5%C9",
	"category" : "Import-Export"
}

addon_name = "CM3D2 Converter"
preview_collections = {}

# このアドオンの設定値群を呼び出す
def preferences():
	return bpy.context.user_preferences.addons[__name__.split('.')[0]].preferences

# データ名末尾の「.001」などを削除
def remove_serial_number(name, enable=True):
	return re.sub(r'\.\d{3,}$', "", name) if enable else name

# 文字列の左右端から空白を削除
def line_trim(line, enable=True):
	return line.strip(' 　\t\r\n') if enable else line

# CM3D2専用ファイル用の文字列書き込み
def write_str(file, raw_str):
	b_str = format(len(raw_str.encode('utf-8')), 'b')
	for i in range(9):
		if 7 < len(b_str):
			file.write( struct.pack('<B', int("1"+b_str[-7:], 2)) )
			b_str = b_str[:-7]
		else:
			file.write( struct.pack('<B', int(b_str, 2)) )
			break
	file.write(raw_str.encode('utf-8'))

# CM3D2専用ファイル用の文字列読み込み
def read_str(file, total_b = ""):
	for i in range(9):
		b_str = format(struct.unpack('<B', file.read(1))[0], '08b')
		total_b = b_str[1:] + total_b
		if b_str[0] == '0': break
	return file.read(int(total_b, 2)).decode('utf-8')

# ボーン/ウェイト名を Blender → CM3D2
def encode_bone_name(name, enable=True):
	return re.sub(r'([_ ])\*([_ ].*)\.([rRlL])$', r'\1\3\2', name) if name.count('*') == 1 and enable else name

# ボーン/ウェイト名を CM3D2 → Blender
def decode_bone_name(name, enable=True):
	return re.sub(r'([_ ])([rRlL])([_ ].*)$', r'\1*\3.\2', name) if enable else name

# CM3D2用マテリアルを設定に合わせて装飾
def decorate_material(mate, enable=True, me=None, mate_index=-1):
	if not enable: return
	if 'shader1' not in mate: return
	
	shader = mate['shader1']
	if 'CM3D2/Man' == shader:
		mate.use_shadeless = True
		mate.diffuse_color = (0, 1, 1)
	elif 'CM3D2/Mosaic' == shader:
		mate.use_transparency = True
		mate.transparency_method = 'RAYTRACE'
		mate.alpha = 0.25
		mate.raytrace_transparency.ior = 2
	elif 'CM3D2_Debug/Debug_CM3D2_Normal2Color' == shader:
		mate.use_tangent_shading = True
		mate.diffuse_color = (0.5, 0.5, 1)
	
	else:
		if '/Toony_' in shader:
			mate.diffuse_shader = 'TOON'
			mate.diffuse_toon_smooth = 0.01
			mate.diffuse_toon_size = 1.2
		if 'Trans' in  shader:
			mate.use_transparency = True
			mate.alpha = 0.0
			mate.texture_slots[0].use_map_alpha = True
		if 'Unlit/' in shader:
			mate.emit = 0.5
		if '_NoZ' in shader:
			mate.offset_z = 9999
	
	is_colored = False
	is_textured = [False, False, False, False]
	rimcolor, rimpower, rimshift = mathutils.Color((1, 1, 1)), 0.0, 0.0
	for slot in mate.texture_slots:
		if not slot: continue
		if not slot.texture: continue
		
		tex = slot.texture
		tex_name = remove_serial_number(tex.name)
		slot.use_map_color_diffuse = False
		
		if tex_name == '_MainTex':
			slot.use_map_color_diffuse = True
			if 'image' in dir(tex):
				img = tex.image
				if len(img.pixels):
					if me:
						color = mathutils.Color(get_image_average_color_uv(img, me, mate_index)[:3])
					else:
						color = mathutils.Color(get_image_average_color(img)[:3])
					mate.diffuse_color = color
					is_colored = True
		
		elif tex_name == '_RimColor':
			rimcolor = slot.color[:]
			if not is_colored:
				mate.diffuse_color = slot.color[:]
				mate.diffuse_color.v += 0.5
		
		elif tex_name == '_Shininess':
			mate.specular_intensity = slot.diffuse_color_factor
		
		elif tex_name == '_RimPower':
			rimpower = slot.diffuse_color_factor
		
		elif tex_name == '_RimShift':
			rimshift = slot.diffuse_color_factor
		
		for index, name in enumerate(['_MainTex', '_ToonRamp', '_ShadowTex', '_ShadowRateToon']):
			if tex_name == name:
				if 'image' in dir(tex):
					if tex.image:
						if len(tex.image.pixels):
							is_textured[index] = tex
		
		set_texture_color(slot)
	
	# よりオリジナルに近く描画するノード作成
	if all(is_textured):
		mate.use_nodes = True
		mate.use_shadeless = True
		
		node_tree = mate.node_tree
		for node in node_tree.nodes[:]:
			node_tree.nodes.remove(node)
		
		mate_node = node_tree.nodes.new('ShaderNodeExtendedMaterial')
		mate_node.location = (0, 0)
		mate_node.material = mate
		
		if "CM3D2 Shade" in bpy.context.blend_data.materials:
			shade_mate = bpy.context.blend_data.materials["CM3D2 Shade"]
		else:
			shade_mate = bpy.context.blend_data.materials.new("CM3D2 Shade")
		shade_mate.diffuse_color = (1, 1, 1)
		shade_mate.diffuse_intensity = 1
		shade_mate.specular_intensity = 1
		shade_mate_node = node_tree.nodes.new('ShaderNodeExtendedMaterial')
		shade_mate_node.location = (234.7785, -131.8243)
		shade_mate_node.material = shade_mate
		
		toon_node = node_tree.nodes.new('ShaderNodeValToRGB')
		toon_node.location = (571.3662, -381.0965)
		toon_img = is_textured[1].image
		toon_w, toon_h = toon_img.size[0], toon_img.size[1]
		for i in range(32 - 2):
			toon_node.color_ramp.elements.new(0.0)
		for i in range(32):
			pos = i / (32 - 1)
			toon_node.color_ramp.elements[i].position = pos
			x = int( (toon_w / (32 - 1)) * i )
			pixel_index = x * toon_img.channels
			toon_node.color_ramp.elements[i].color = toon_img.pixels[pixel_index:pixel_index+4]
		toon_node.color_ramp.interpolation = 'EASE'
		
		shadow_rate_node = node_tree.nodes.new('ShaderNodeValToRGB')
		shadow_rate_node.location = (488.2785, 7.8446)
		shadow_rate_img = is_textured[3].image
		shadow_rate_w, shadow_rate_h = shadow_rate_img.size[0], shadow_rate_img.size[1]
		for i in range(32 - 2):
			shadow_rate_node.color_ramp.elements.new(0.0)
		for i in range(32):
			pos = i / (32 - 1)
			shadow_rate_node.color_ramp.elements[i].position = pos
			x = int( (shadow_rate_w / (32)) * i )
			pixel_index = x * shadow_rate_img.channels
			shadow_rate_node.color_ramp.elements[i].color = shadow_rate_img.pixels[pixel_index:pixel_index+4]
		shadow_rate_node.color_ramp.interpolation = 'EASE'
		
		geometry_node = node_tree.nodes.new('ShaderNodeGeometry')
		geometry_node.location = (323.4597, -810.8045)
		
		shadow_texture_node = node_tree.nodes.new('ShaderNodeTexture')
		shadow_texture_node.location = (626.0117, -666.0227)
		shadow_texture_node.texture = is_textured[2]
		
		invert_node = node_tree.nodes.new('ShaderNodeInvert')
		invert_node.location = (805.6814, -132.9144)
		
		shadow_mix_node = node_tree.nodes.new('ShaderNodeMixRGB')
		shadow_mix_node.location = (1031.2714, -201.5598)
		
		toon_mix_node = node_tree.nodes.new('ShaderNodeMixRGB')
		toon_mix_node.location = (1257.5538, -308.8037)
		toon_mix_node.blend_type = 'MULTIPLY'
		toon_mix_node.inputs[0].default_value = 1.0
		
		specular_mix_node = node_tree.nodes.new('ShaderNodeMixRGB')
		specular_mix_node.location = (1473.2079, -382.7421)
		specular_mix_node.blend_type = 'SCREEN'
		specular_mix_node.inputs[0].default_value = mate.specular_intensity
		
		normal_node = node_tree.nodes.new('ShaderNodeNormal')
		normal_node.location = (912.1372, -590.8748)
		
		rim_ramp_node = node_tree.nodes.new('ShaderNodeValToRGB')
		rim_ramp_node.location = (1119.0664, -570.0284)
		rim_ramp_node.color_ramp.elements[0].color = list(rimcolor[:]) + [1.0]
		rim_ramp_node.color_ramp.elements[0].position = rimshift
		rim_ramp_node.color_ramp.elements[1].color = (0, 0, 0, 1)
		rim_ramp_node.color_ramp.elements[1].position = (rimshift) + ((1.0 - (rimpower * 0.03333)) * 0.5)
		
		rim_power_node = node_tree.nodes.new('ShaderNodeHueSaturation')
		rim_power_node.location = (1426.6332, -575.6142)
		#rim_power_node.inputs[2].default_value = rimpower * 0.1
		
		rim_mix_node = node_tree.nodes.new('ShaderNodeMixRGB')
		rim_mix_node.location = (1724.7024, -451.9624)
		rim_mix_node.blend_type = 'ADD'
		
		out_node = node_tree.nodes.new('ShaderNodeOutput')
		out_node.location = (1957.4023, -480.5365)
		
		node_tree.links.new(shadow_mix_node.inputs[1], mate_node.outputs[0])
		node_tree.links.new(shadow_rate_node.inputs[0], shade_mate_node.outputs[3])
		node_tree.links.new(invert_node.inputs[1], shadow_rate_node.outputs[0])
		node_tree.links.new(shadow_mix_node.inputs[0], invert_node.outputs[0])
		node_tree.links.new(toon_node.inputs[0], shade_mate_node.outputs[3])
		node_tree.links.new(shadow_texture_node.inputs[0], geometry_node.outputs[4])
		node_tree.links.new(shadow_mix_node.inputs[2], shadow_texture_node.outputs[1])
		node_tree.links.new(toon_node.inputs[0], shade_mate_node.outputs[3])
		node_tree.links.new(toon_mix_node.inputs[1], shadow_mix_node.outputs[0])
		node_tree.links.new(toon_mix_node.inputs[2], toon_node.outputs[0])
		node_tree.links.new(specular_mix_node.inputs[1], toon_mix_node.outputs[0])
		node_tree.links.new(specular_mix_node.inputs[2], shade_mate_node.outputs[4])
		node_tree.links.new(normal_node.inputs[0], mate_node.outputs[2])
		node_tree.links.new(rim_ramp_node.inputs[0], normal_node.outputs[1])
		node_tree.links.new(rim_power_node.inputs[4], rim_ramp_node.outputs[0])
		node_tree.links.new(rim_mix_node.inputs[2], rim_power_node.outputs[0])
		node_tree.links.new(rim_mix_node.inputs[0], shadow_rate_node.outputs[0])
		node_tree.links.new(rim_mix_node.inputs[1], specular_mix_node.outputs[0])
		node_tree.links.new(out_node.inputs[0], rim_mix_node.outputs[0])
		node_tree.links.new(out_node.inputs[1], mate_node.outputs[1])
		
		for node in node_tree.nodes[:]:
			node.select = False
		node_tree.nodes.active = mate_node
		node_tree.nodes.active.select = True
	
	else:
		mate.use_nodes = False
		mate.use_shadeless = False

# 画像のおおよその平均色を取得
def get_image_average_color(img, sample_count=10):
	if not len(img.pixels): return mathutils.Color([0, 0, 0])
	
	pixel_count = img.size[0] * img.size[1]
	channels = img.channels
	
	max_s = 0.0
	max_s_color, average_color = mathutils.Color([0, 0, 0]), mathutils.Color([0, 0, 0])
	seek_interval = pixel_count / sample_count
	for sample_index in range(sample_count):
		
		index = int(seek_interval * sample_index) * channels
		color = mathutils.Color(img.pixels[index:index+3])
		average_color += color
		if max_s < color.s:
			max_s_color, max_s = color, color.s
	
	average_color /= sample_count
	output_color = (average_color + max_s_color) / 2
	output_color.s *= 1.5
	return max_s_color

# 画像のおおよその平均色を取得 (UV版)
def get_image_average_color_uv(img, me=None, mate_index=-1, sample_count=10):
	if not len(img.pixels): return mathutils.Color([0, 0, 0])
	
	img_width, img_height, img_channel = img.size[0], img.size[1], img.channels
	
	bm = bmesh.new()
	bm.from_mesh(me)
	uv_lay = bm.loops.layers.uv.active
	uvs = [l[uv_lay].uv[:] for f in bm.faces if f.material_index == mate_index for l in f.loops]
	bm.free()
	
	if len(uvs) <= sample_count:
		return get_image_average_color(img)
	
	average_color = mathutils.Color([0, 0, 0])
	max_s = 0.0
	max_s_color = mathutils.Color([0, 0, 0])
	seek_interval = len(uvs) / sample_count
	for sample_index in range(sample_count):
		
		uv_index = int(seek_interval * sample_index)
		x, y = uvs[uv_index]
		
		x = math.modf(x)[0]
		if x < 0.0: x += 1.0
		y = math.modf(y)[0]
		if y < 0.0: y += 1.0
		
		x, y = int(x * img_width), int(y * img_height)
		
		pixel_index = ((y * img_width) + x) * img_channel
		color = mathutils.Color(img.pixels[pixel_index:pixel_index+3])
		
		average_color += color
		if max_s < color.s:
			max_s_color, max_s = color, color.s
	
	average_color /= sample_count
	output_color = (average_color + max_s_color) / 2
	output_color.s *= 1.5
	return output_color

# CM3D2のインストールフォルダを取得＋α
def default_cm3d2_dir(base_dir, file_name, new_ext):
	if not base_dir:
		if preferences().cm3d2_path:
			base_dir = os.path.join(preferences().cm3d2_path, "GameData", "*." + new_ext)
		else:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					base_dir = winreg.QueryValueEx(key, 'InstallPath')[0]
					preferences().cm3d2_path = base_dir
					base_dir = os.path.join(base_dir, "GameData", "*." + new_ext)
			except: pass
	if file_name:
		base_dir = os.path.join(os.path.split(base_dir)[0], file_name)
	base_dir = os.path.splitext(base_dir)[0] + "." + new_ext
	return base_dir

# 一時ファイル書き込みと自動バックアップを行うファイルオブジェクトを返す
def open_temporary(filepath, mode, is_backup=False):
	backup_ext = preferences().backup_ext
	if is_backup and backup_ext:
		backup_filepath = filepath + '.' + backup_ext
	else:
		backup_filepath = None
	return fileutil.TemporaryFileWriter(filepath, mode, backup_filepath=backup_filepath)

# ファイルを上書きするならバックアップ処理
def file_backup(filepath, enable=True):
	backup_ext = preferences().backup_ext
	if enable and backup_ext and os.path.exists(filepath):
		shutil.copyfile(filepath, filepath+"."+backup_ext)

# サブフォルダを再帰的に検索してリスト化
def fild_tex_all_files(dir):
	for root, dirs, files in os.walk(dir):
		yield root
		for file in files:
			if os.path.splitext(file)[1].lower() == ".tex":
				yield os.path.join(root, file)
			elif os.path.splitext(file)[1].lower() == ".png":
				yield os.path.join(root, file)

# テクスチャ置き場のパスのリストを返す
def get_default_tex_paths():
	default_paths = [preferences().default_tex_path0, preferences().default_tex_path1, preferences().default_tex_path2, preferences().default_tex_path3]
	if not any(default_paths):
		
		cm3d2_dir = preferences().cm3d2_path
		if not cm3d2_dir:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					cm3d2_dir = winreg.QueryValueEx(key, 'InstallPath')[0]
			except: return []
		
		target_dir = [os.path.join(cm3d2_dir, "GameData", "texture")]
		target_dir.append(os.path.join(cm3d2_dir, "GameData", "texture2"))
		target_dir.append(os.path.join(cm3d2_dir, "Sybaris", "GameData"))
		target_dir.append(os.path.join(cm3d2_dir, "Mod"))
		
		tex_dirs = [path for path in target_dir if os.path.isdir(path)]
		
		for index, path in enumerate(tex_dirs):
			preferences().__setattr__('default_tex_path' + str(index), path)
	else:
		tex_dirs = [preferences().__getattribute__('default_tex_path' + str(i)) for i in range(4) if preferences().__getattribute__('default_tex_path' + str(i))]
	return tex_dirs

# テクスチャ置き場の全ファイルを返す
def get_tex_storage_files():
	files = []
	tex_dirs = get_default_tex_paths()
	for tex_dir in tex_dirs:
		tex_dir = bpy.path.abspath(tex_dir)
		files.extend(fild_tex_all_files(tex_dir))
	return files

# テクスチャを検索して空の画像へ置換
def replace_cm3d2_tex(img, pre_files=[]):
	source_png_name = remove_serial_number(img.name).lower() + ".png"
	source_tex_name = remove_serial_number(img.name).lower() + ".tex"
	
	tex_dirs = get_default_tex_paths()
	
	for tex_dir in tex_dirs:
		
		if len(pre_files):
			files = pre_files
		else:
			files = fild_tex_all_files(tex_dir)
		
		for path in files:
			path = bpy.path.abspath(path)
			file_name = os.path.basename(path).lower()
			
			if file_name == source_png_name:
				img.filepath = path
				img.reload()
				return True
			
			elif file_name == source_tex_name:
				try:
					file = open(path, 'rb')
				except: return False
				
				header_ext = read_str(file)
				if header_ext == 'CM3D2_TEX':
					file.seek(4, 1)
					read_str(file)
					png_size = struct.unpack('<i', file.read(4))[0]
					png_path = os.path.splitext(path)[0] + ".png"
					try:
						png_file = open(png_path, 'wb')
					except: return False
					png_file.write(file.read(png_size))
					png_file.close() ; file.close()
					img.filepath = png_path
					img.reload()
					return True
				else:
					file.close()
					return False
		
		if len(pre_files):
			return False
	return False

# col f タイプの設定値を値に合わせて着色
def set_texture_color(slot):
	if not slot or not slot.texture or slot.use: return
	
	type = 'col' if slot.use_rgb_to_intensity else 'f'
	tex = slot.texture
	base_name = remove_serial_number(tex.name)
	tex.type = 'BLEND'
	if 'progression' in dir(tex):
		tex.progression = 'DIAGONAL'
	tex.use_color_ramp = True
	tex.use_preview_alpha = True
	elements = tex.color_ramp.elements
	
	element_count = 4
	if element_count < len(elements):
		for i in range(len(elements) - element_count):
			elements.remove(elements[-1])
	elif len(elements) < element_count:
		for i in range(element_count - len(elements)):
			elements.new(1.0)
	
	elements[0].position, elements[1].position, elements[2].position, elements[3].position = 0.2, 0.21, 0.25, 0.26
	
	if type == 'col':
		elements[0].color = [0.2, 1, 0.2, 1]
		elements[-1].color = slot.color[:] + (slot.diffuse_color_factor, )
		if 0.3 < mathutils.Color(slot.color[:3]).v:
			elements[1].color, elements[2].color = [0, 0, 0, 1], [0, 0, 0, 1]
		else:
			elements[1].color, elements[2].color = [1, 1, 1, 1], [1, 1, 1, 1]
	
	elif type == 'f':
		elements[0].color = [0.2, 0.2, 1, 1]
		multi = 1.0
		if base_name == '_OutlineWidth':
			multi = 200
		elif base_name == '_RimPower':
			multi = 1.0 / 30.0
		value = slot.diffuse_color_factor * multi
		elements[-1].color = [value, value, value, 1]
		if 0.3 < value:
			elements[1].color, elements[2].color = [0, 0, 0, 1], [0, 0, 0, 1]
		else:
			elements[1].color, elements[2].color = [1, 1, 1, 1], [1, 1, 1, 1]

# 必要なエリアタイプを設定を変更してでも取得
def get_request_area(context, request_type, except_types=['VIEW_3D', 'PROPERTIES', 'INFO', 'USER_PREFERENCES']):
	request_areas = [(a, a.width * a.height) for a in context.screen.areas if a.type == request_type]
	candidate_areas = [(a, a.width * a.height) for a in context.screen.areas if a.type not in except_types]
	
	return_areas = request_areas[:] if len(request_areas) else candidate_areas
	if not len(return_areas): return None
	
	return_areas.sort(key=lambda i: i[1])
	return_area = return_areas[-1][0]
	return_area.type = request_type
	return return_area

# 複数のデータを完全に削除
def remove_data(target_data):
	try: target_data = target_data[:]
	except: target_data = [target_data]
	
	for data in target_data:
		if data.__class__.__name__ == 'Object':
			if data.name in bpy.context.scene.objects:
				bpy.context.scene.objects.unlink(data)
	
	for data in target_data:
		if 'users' in dir(data) and 'user_clear' in dir(data):
			if data.users: data.user_clear()
	
	for data in target_data:
		for data_str in dir(bpy.data):
			if data_str[-1] != "s": continue
			try:
				if data.__class__.__name__ == eval('bpy.data.%s[0].__class__.__name__' % data_str):
					exec('bpy.data.%s.remove(data, do_unlink=True)' % data_str)
					break
			except: pass

# オブジェクトのマテリアルを削除/復元するクラス
class material_restore:
	def __init__(self, ob):
		override = bpy.context.copy()
		override['object'] = ob
		self.object = ob
		
		self.slots = []
		for slot in ob.material_slots:
			if slot: self.slots.append(slot.material)
			else: self.slots.append(None)
		
		self.mesh_data = []
		for index, slot in enumerate(ob.material_slots):
			self.mesh_data.append([])
			for face in ob.data.polygons:
				if face.material_index == index:
					self.mesh_data[-1].append(face.index)
		
		for slot in ob.material_slots[:]:
			bpy.ops.object.material_slot_remove(override)
	
	def restore(self):
		override = bpy.context.copy()
		override['object'] = self.object
		
		for slot in self.object.material_slots[:]:
			bpy.ops.object.material_slot_remove(override)
		
		for index, mate in enumerate(self.slots):
			bpy.ops.object.material_slot_add(override)
			slot = self.object.material_slots[index]
			if slot:
				slot.material = mate
			for face_index in self.mesh_data[index]:
				self.object.data.polygons[face_index].material_index = index

# 現在のレイヤー内のオブジェクトをレンダリングしなくする/戻す
class hide_render_restore:
	def __init__(self, render_objects=[]):
		try: render_objects = render_objects[:]
		except: render_objects = [render_objects]
		
		if not len(render_objects):
			render_objects = bpy.context.selected_objects[:]
		
		self.render_objects = render_objects[:]
		self.render_object_names = [ob.name for ob in render_objects]
		
		self.rendered_objects = []
		for ob in render_objects:
			if ob.hide_render:
				self.rendered_objects.append(ob)
				ob.hide_render = False
		
		self.hide_rendered_objects = []
		for ob in bpy.data.objects:
			for layer_index, is_used in enumerate(bpy.context.scene.layers):
				if not is_used: continue
				if ob.layers[layer_index] and is_used and ob.name not in self.render_object_names and not ob.hide_render:
					self.hide_rendered_objects.append(ob)
					ob.hide_render = True
					break
	
	def restore(self):
		for ob in self.rendered_objects:
			ob.hide_render = True
		for ob in self.hide_rendered_objects:
			ob.hide_render = False

# 指定エリアに変数をセット
def set_area_space_attr(area, attr_name, value):
	if not area: return
	for space in area.spaces:
		if space.type == area.type:
			space.__setattr__(attr_name, value)
			break

# スムーズなグラフを返す1
def in_out_quad_blend(f):
	if f <= 0.5:
		return 2.0 * math.sqrt(f)
	f -= 0.5
	return 2.0 * f * (1.0 - f) + 0.5
# スムーズなグラフを返す2
def bezier_blend(f):
	return math.sqrt(f) * (3.0 - 2.0 * f)
# sin((x-0.25)*pi*2)*0.5+0.5

# エクスポート例外クラス
class CM3D2ExportException(Exception):
	pass
