import sys
import os
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget, QApplication
from PyQt5.QtCore import Qt, QTimer
import OpenGL.GL as GL
from abc import abstractmethod

def compile_shader(shader_src, shader_type):
    shader = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader, shader_src)
    GL.glCompileShader(shader)
    status = GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS)
    if not status:
        msg = GL.glGetShaderInfoLog(shader)
        raise RuntimeError(msg)

    return shader


def create_program(vs, fs):
    vertex_shader = compile_shader(vs, GL.GL_VERTEX_SHADER)
    frag_shader = compile_shader(fs, GL.GL_FRAGMENT_SHADER)
    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, frag_shader)
    GL.glLinkProgram(program)
    status = GL.glGetProgramiv(program, GL.GL_LINK_STATUS)
    if not status:
        msg = GL.glGetProgramInfoLog(program)
        raise RuntimeError(msg)

    return program


def create_vao(v_pos, uv_coord):
    vao = GL.glGenVertexArrays(1)
    vbo = GL.glGenBuffers(1)
    uvbo = GL.glGenBuffers(1)
    GL.glBindVertexArray(vao)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, v_pos.nbytes, v_pos, GL.GL_DYNAMIC_DRAW)
    GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, 0, None)
    GL.glEnableVertexAttribArray(0)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, uvbo)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, uv_coord.nbytes, uv_coord, GL.GL_DYNAMIC_DRAW)
    GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, False, 0, None)
    GL.glEnableVertexAttribArray(1)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    GL.glBindVertexArray(0)
    return vao


def create_canvas_framebuffer(width, height):
    old_fbo = GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING)
    fbo = GL.glGenFramebuffers(1)

    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fbo)

    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA,
                    width, height,
                    0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, texture, 0)

    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, old_fbo)
    return fbo, texture


class OpenGLCanvas(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__canvas_opacity = 1.0
        self._program = None
        self._vao = None
        self._canvas_framebuffer = None
        self._canvas_texture = None
        self._opacity_loc = None

    def __create_program(self):
        vertex_shader = """#version 330 core
        layout(location = 0) in vec2 a_position;
        layout(location = 1) in vec2 a_texCoord;
        out vec2 v_texCoord;
        void main() {
            gl_Position = vec4(a_position, 0.0, 1.0);
            v_texCoord = a_texCoord;
        }
        """
        frag_shader = """#version 330 core
        in vec2 v_texCoord;
        uniform sampler2D canvas;
        uniform float opacity;
        void main() {
            vec4 color = texture(canvas, v_texCoord);
            color *= opacity;
            gl_FragColor =  color;
        }
        """
        self._program = create_program(vertex_shader, frag_shader)
        self._opacity_loc = GL.glGetUniformLocation(self._program, "opacity")

    def __create_vao(self):
        vertices = np.array([
            # 位置
            -1, 1,
            -1, -1,
            1, -1,
            -1, 1,
            1, -1,
            1, 1,
        ], dtype=np.float32)
        uvs = np.array([
            # 纹理坐标
            0, 1,
            0, 0,
            1, 0,
            0, 1,
            1, 0,
            1, 1
        ], dtype=np.float32)
        self._vao = create_vao(vertices, uvs)

    def __create_canvas_framebuffer(self):
        self._canvas_framebuffer, self._canvas_texture = create_canvas_framebuffer(
            max(1, self.width()), max(1, self.height())
        )

    def __draw_on_canvas(self):
        old_fbo = GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._canvas_framebuffer)
        self.on_draw()
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, old_fbo)

    def initializeGL(self):
        self.__create_program()
        self.__create_vao()
        self.__create_canvas_framebuffer()
        self.on_init()

    def resizeGL(self, w, h):
        if hasattr(self, '_canvas_framebuffer') and self._canvas_framebuffer is not None:
            # Delete old framebuffer and texture
            GL.glDeleteFramebuffers(1, [self._canvas_framebuffer])
            GL.glDeleteTextures(1, [self._canvas_texture])
            # Create new ones with proper size
            self.__create_canvas_framebuffer()
        self.on_resize(w, h)

    def paintGL(self):
        self.__draw_on_canvas()
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glBindVertexArray(self._vao)
        GL.glUseProgram(self._program)
        GL.glProgramUniform1f(self._program, self._opacity_loc, self.__canvas_opacity)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._canvas_texture)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)
        GL.glBindVertexArray(0)
    
    def setCanvasOpacity(self, value):
        self.__canvas_opacity = value

    @abstractmethod
    def on_init(self):
        pass

    @abstractmethod
    def on_draw(self):
        pass

    @abstractmethod
    def on_resize(self, width: int, height: int):
        pass


class Live2DWidget(OpenGLCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = None
        self.live2d_module = None
        self.model_path = None
        self.is_initialized = False
        self.is_loading = False
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Setup animation timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(1000 // 60)  # 60 FPS refresh rate

    def on_init(self):
        try:
            import live2d.v3 as live2d
            self.live2d_module = live2d
            live2d.glewInit()
            self.is_initialized = True
        except ImportError as e:
            print(f"Failed to initialize Live2D: {e}")
            self.is_initialized = False
    
    def on_draw(self):
        if not self.is_initialized or self.model is None:
            return
            
        try:
            self.live2d_module.clearBuffer()
            self.model.Update()
            self.model.Draw()
        except Exception as e:
            print(f"Error drawing Live2D model: {e}")

    def on_resize(self, width: int, height: int):
        if self.model is not None and self.is_initialized:
            try:
                self.model.Resize(width, height)
            except Exception as e:
                print(f"Error resizing model: {e}")

    def load(self, model_path):
        """Load a Live2D model from the given path"""
        if not self.is_initialized or self.is_loading:
            return False
        
        # Check for valid model path
        if not os.path.exists(model_path):
            print(f"Model file not found: {model_path}")
            return False
            
        try:
            self.is_loading = True
            self.release()  # Release previous model if any
            
            # Create and load model
            self.model = self.live2d_module.LAppModel()
            self.model.LoadModelJson(model_path)
            self.model.Resize(self.width(), self.height())
            self.model_path = model_path
            self.is_loading = False
            return True
        except Exception as e:
            print(f"Failed to load Live2D model: {e}")
            self.model = None
            self.model_path = None
            self.is_loading = False
            return False

    def release(self):
        """Release the current model"""
        if self.model is not None:
            try:
                self.model = None
                self.model_path = None
            except Exception as e:
                print(f"Error releasing model: {e}")

    def mouseMoveEvent(self, event):
        """Handle mouse movement for interacting with the model"""
        if self.model is not None and self.is_initialized:
            try:
                self.model.Drag(event.x(), event.y())
                self.update()
            except Exception as e:
                print(f"Error handling mouse movement: {e}")
        super().mouseMoveEvent(event)
