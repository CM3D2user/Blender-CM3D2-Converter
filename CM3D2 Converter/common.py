import bpy, os, re, struct, shutil

preview_collections = {}

def preferences():
	return bpy.context.user_preferences.addons[__name__.split('.')[0]].preferences

def remove_serial_number(name, enable=True):
	if enable:
		return re.sub(r'\.\d{3,}$', "", name)
	return name

def line_trim(line, enable=True):
	if enable:
		line = re.sub(r'^[ 　\t\r\n]*', "", line)
		return re.sub(r'[ 　\t\r\n]*$', "", line)
	return line

def write_str(file, s):
	str_count = len(s.encode('utf-8'))
	if 128 <= str_count:
		b = (str_count % 128) + 128
		file.write(struct.pack('<B', b))
		b = str_count // 128
		file.write(struct.pack('<B', b))
	else:
		file.write(struct.pack('<B', str_count))
	file.write(s.encode('utf-8'))

def read_str(file):
	str_index = struct.unpack('<B', file.read(1))[0]
	if 128 <= str_index:
		i = struct.unpack('<B', file.read(1))[0]
		str_index += (i * 128) - 128
	return file.read(str_index).decode('utf-8')

def encode_bone_name(name, enable=True):
	if not enable:
		return name
	if name.count('*') == 1:
		direction = re.search(r'\.([rRlL])$', name)
		if direction:
			direction = direction.groups()[0]
			name = re.sub(r'\.[rRlL]$', '', name)
			name = re.sub(r'([_ ])\*([_ ])', r'\1'+direction+r'\2', name)
	return name

def decode_bone_name(name, enable=True):
	if not enable:
		return name
	direction = re.search(r'[_ ]([rRlL])[_ ]', name)
	if direction:
		direction = direction.groups()[0]
		name = re.sub(r'([_ ])[rRlL]([_ ])', r'\1*\2', name) + "." + direction
	return name

def decorate_material(mate, shader_str, enable=True):
	if not enable:
		return
	
	if 'shader1' not in mate.keys():
		return
	shader_str = mate['shader1']
	
	if '/Toony_' in shader_str:
		mate.diffuse_shader = 'TOON'
		mate.diffuse_toon_smooth = 0.01
		mate.diffuse_toon_size = 1.2
	if 'Trans' in  shader_str:
		mate.use_transparency = True
		mate.alpha = 0.0
		mate.texture_slots[0].use_map_alpha = True
	if 'Unlit/' in shader_str:
		mate.emit = 0.5
	if '_NoZ' in shader_str:
		mate.offset_z = 9999
	if 'CM3D2/Man' == shader_str:
		mate.use_shadeless = True
	if 'CM3D2/Mosaic' == shader_str:
		mate.use_transparency = True
		mate.transparency_method = 'RAYTRACE'
		mate.alpha = 0.25
		mate.raytrace_transparency.ior = 2
	
	slot = mate.texture_slots[0]
	if slot:
		tex = slot.texture
		if tex:
			if remove_serial_number(tex.name) == '_MainTex':
				if 'image' in dir(tex):
					img = tex.image
					if len(img.pixels):
						mate.diffuse_color = get_image_average_color(img)[:3]

def get_image_average_color(img, sample_count=10, enable=True):
	if not len(img.pixels):
		return [0, 0, 0, 0]
	
	pixel_count = img.size[0] * img.size[1]
	channels = img.channels
	
	average_color = [0] * channels
	seek_interval = pixel_count / sample_count
	for sample_index in range(sample_count):
		for channel_index in range(channels):
			index = int(seek_interval * sample_index) * channels + channel_index
			average_color[channel_index] += img.pixels[index]
	
	for channel_index in range(channels):
		average_color[channel_index] /= sample_count
	return average_color

def default_cm3d2_dir(main_dir, file_name, replace_ext):
	if not main_dir:
		try:
			import winreg
			with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
				main_dir = winreg.QueryValueEx(key, 'InstallPath')[0]
				main_dir = os.path.join(main_dir, "GameData", "*." + replace_ext)
		except:
			pass
	if file_name:
		head, tail = os.path.split(main_dir)
		main_dir = os.path.join(head, file_name)
	root, ext = os.path.splitext(main_dir)
	main_dir = root + "." + replace_ext
	return main_dir

def file_backup(filepath, enable=True):
	backup_ext = bpy.context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext
	if enable and backup_ext:
		if os.path.exists(filepath):
			backup_path = filepath + "." + backup_ext
			shutil.copyfile(filepath, backup_path)

def fild_all_files(directory):
	for root, dirs, files in os.walk(directory):
		yield root
		for file in files:
			yield os.path.join(root, file)

def replace_cm3d2_tex(img):
	default_tex_paths = [preferences().default_tex_path0, preferences().default_tex_path1, preferences().default_tex_path2, preferences().default_tex_path3]
	for i, path in enumerate(default_tex_paths):
		default_tex_paths[i] = bool(path)
	if True not in default_tex_paths:
		try:
			import winreg
			with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
				cm3d2_dir = winreg.QueryValueEx(key, 'InstallPath')[0]
		except:
			return False
		
		target_dir = [os.path.join(cm3d2_dir, "GameData", "texture")]
		target_dir.append(os.path.join(cm3d2_dir, "GameData", "texture2"))
		target_dir.append(os.path.join(cm3d2_dir, "Sybaris", "GameData"))
		target_dir.append(os.path.join(cm3d2_dir, "Mod"))
		
		tex_dirs = []
		for path in target_dir:
			if os.path.isdir(path):
				tex_dirs.append(path)
		
		for index, path in enumerate(tex_dirs):
			preferences().__setattr__('default_tex_path' + str(index), path)
	else:
		tex_dirs = []
		for index in range(4):
			tex_dirs.append( preferences().__getattribute__('default_tex_path' + str(index)) )
	
	if 'cm3d2_path' in img.keys():
		source_path = img['cm3d2_path']
	else:
		img['cm3d2_path'] = img.filepath
		source_path = img.filepath
	source_png_name = os.path.basename(source_path).lower()
	if '*' in source_png_name:
		source_png_name = remove_serial_number(img.name)
	source_tex_name = os.path.splitext(source_png_name)[0] + ".tex"
	
	for tex_dir in tex_dirs:
		for path in fild_all_files(tex_dir):
			file_name = os.path.basename(path).lower()
			
			if file_name == source_png_name:
				img.filepath = path
				img.reload()
				return True
			else:
				if file_name == source_tex_name:
					file = open(path, 'rb')
					header_ext = read_str(file)
					if header_ext == 'CM3D2_TEX':
						file.seek(4, 1)
						read_str(file)
						png_size = struct.unpack('<i', file.read(4))[0]
						png_path = os.path.splitext(path)[0] + ".png"
						png_file = open(png_path, 'wb')
						png_file.write(file.read(png_size))
						png_file.close()
						file.close()
						img.filepath = png_path
						img.reload()
						return True
					else:
						file.close()
						return False
	return False

def set_texture_color(slot):
	if not slot:
		return
	if not slot.texture:
		return
	if slot.use:
		return
	if slot.use_rgb_to_intensity:
		type = 'col'
	else:
		type = 'f'
	
	tex = slot.texture
	base_name = remove_serial_number(tex.name)
	tex.type = 'BLEND'
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
	
	elements[0].position = 0.2
	elements[1].position = 0.21
	elements[2].position = 0.3
	elements[3].position = 0.31
	elements[1].color = [0, 0, 0, 1]
	elements[2].color = [0, 0, 0, 1]
	
	if type == 'col':
		elements[0].color = [0.5, 1, 0.5, 1]
		color = list(slot.color[:])
		color.append(slot.diffuse_color_factor)
		elements[-1].color = color
	
	elif type == 'f':
		elements[0].color = [0.5, 0.5, 1, 1]
		multi = 1.0
		if base_name == '_OutlineWidth':
			multi = 200
		elif base_name == '_RimPower':
			multi = 1.0 / 30.0
		value = slot.diffuse_color_factor * multi
		elements[-1].color = [value, value, value, 1]
	
	else:
		elements[0].color = [1, 0, 1, 1]
		elements[1].color = [1, 0, 1, 1]
		elements[2].color = [1, 0, 1, 1]
		elements[3].color = [1, 0, 1, 1]
