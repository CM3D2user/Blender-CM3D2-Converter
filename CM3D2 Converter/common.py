import bpy, re, struct

preview_collections = {}

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
