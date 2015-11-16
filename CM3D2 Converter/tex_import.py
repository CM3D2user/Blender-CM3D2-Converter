import bpy, struct, os.path

def ReadStr(file):
	str_index = struct.unpack('<B', file.read(1))[0]
	if 128 <= str_index:
		i = struct.unpack('<B', file.read(1))[0]
		str_index += (i * 128) - 128
	try:
		return file.read(str_index).decode('utf-8')
	except:
		pass
	return None

class import_cm3d2_tex(bpy.types.Operator):
	bl_idname = "image.import_cm3d2_tex"
	bl_label = "texファイルを開く"
	bl_description = "CM3D2で使用されるテクスチャファイル(.tex)を読み込みます"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".tex;.png"
	filter_glob = bpy.props.StringProperty(default="*.tex;*.png", options={'HIDDEN'})
	
	def invoke(self, context, event):
		self.filepath = context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_import_path
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_import_path = self.filepath
		file = open(self.filepath, 'rb')
		header_ext = ReadStr(file)
		if header_ext == 'CM3D2_TEX':
			file.seek(4, 1)
			ReadStr(file)
			png_size = struct.unpack('<i', file.read(4))[0]
			root, ext = os.path.splitext(self.filepath)
			png_path = root + ".png"
			png_file = open(png_path, 'wb')
			png_file.write(file.read(png_size))
			png_file.close()
			bpy.ops.image.open(filepath=png_path)
			context.edit_image.name = os.path.basename(self.filepath)
		else:
			bpy.ops.image.open(filepath=self.filepath)
		file.close()
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.separator()
	self.layout.operator(import_cm3d2_tex.bl_idname, icon='SPACE2')
