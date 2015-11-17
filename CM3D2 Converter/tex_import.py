import os, os.path, bpy, struct, os.path

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
	
	items = [
		('PACK', "内部にパックする", "", 1),
		('PNG', "PNGに変換してPNGを開く", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="展開方法", default='PNG')
	
	def invoke(self, context, event):
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_import_path:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					path = winreg.QueryValueEx(key, 'InstallPath')[0]
					path = os.path.join(path, 'GameData', '*.tex')
					context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_import_path = path
			except:
				pass
		self.filepath = context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_import_path
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'mode', icon='FILESEL')
	
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
			is_png_overwrite = os.path.exists(png_path)
			if self.mode == 'PACK' and is_png_overwrite:
				png_path = png_path + ".temp.png"
			png_file = open(png_path, 'wb')
			png_file.write(file.read(png_size))
			png_file.close()
			bpy.ops.image.open(filepath=png_path)
			img = context.edit_image
			img.name = os.path.basename(self.filepath)
		else:
			bpy.ops.image.open(filepath=self.filepath)
			img = context.edit_image
		file.close()
		if self.mode == 'PACK':
			img.pack(as_png=True)
			if header_ext == 'CM3D2_TEX':
				os.remove(png_path)
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.separator()
	self.layout.operator(import_cm3d2_tex.bl_idname, icon='SPACE2')
