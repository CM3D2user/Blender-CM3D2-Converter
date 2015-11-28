import bpy, os, re, struct, shutil

preview_collections = {}

def preferences():
	return bpy.context.user_preferences.addons[__name__.split('.')[0]].preferences

def remove_serial_number(name, flag=True):
	if flag:
		return re.sub(r'\.\d{3}$', "", name)
	return name

def line_trim(line):
	line = re.sub(r'^[ 　\t\r\n]*', "", line)
	return re.sub(r'[ 　\t\r\n]*$', "", line)

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

def decorate_material(mate, shader_str, flag=True):
	if flag:
		if '/Toony_' in shader_str:
			mate.diffuse_shader = 'TOON'
			mate.diffuse_toon_smooth = 0.01
			mate.diffuse_toon_size = 1.2
		if 'Trans' in  shader_str:
			mate.use_transparency = True
			mate.alpha = 0.5
		if 'CM3D2/Man' in shader_str:
			mate.use_shadeless = True
		if 'Unlit/' in shader_str:
			mate.emit = 0.5
		if '_NoZ' in shader_str:
			mate.offset_z = 9999
		if 'CM3D2/Mosaic' in shader_str:
			mate.use_transparency = True
			mate.transparency_method = 'RAYTRACE'
			mate.alpha = 0.25
			mate.raytrace_transparency.ior = 2

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
	if not preferences().default_tex_path0 and not preferences().default_tex_path1 and not preferences().default_tex_path2:
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

def set_texture_color(tex, color, type, alpha=1.0):
	base_name = remove_serial_number(tex.name)
	tex.type = 'BLEND'
	tex.use_color_ramp = True
	tex.use_preview_alpha = True
	elements = tex.color_ramp.elements
	
	if 2 < len(elements):
		for i in range(len(elements) - 2):
			elements.remove(elements[-1])
	elif len(elements) < 2:
		for i in range(2 - len(elements)):
			elements.new(1.0)
	elements[0].position = 0.2
	elements[1].position = 0.21
	
	if type == 'col':
		elements[0].color = [0.5, 1, 0.5, 1]
		
		try:
			color = list(color[:])
			if len(color) == 3:
				color.append(alpha)
		except:
			color = [color, color, color, alpha]
		elements[1].color = color
	
	elif type == 'f':
		elements[0].color = [0.5, 0.5, 1, 1]
		
		multi = 1.0
		if base_name == '_OutlineWidth':
			multi = 200
		elif base_name == '_RimPower':
			multi = 1.0 / 30.0
		
		value = color * multi
		elements[1].color = [value, value, value, 1]
	
	else:
		elements[0].color = [1, 0, 1, 1]
		elements[1].color = [1, 0, 1, 1]
