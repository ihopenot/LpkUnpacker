import math
import numpy as np
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt
import OpenGL.GL as GL
from abc import abstractmethod

import live2d.v3 as live2d
from live2d.utils.canvas import Canvas

live2d.init()

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
    """创建 VAO/VBO"""

    vao = GL.glGenVertexArrays(1)
    vbo = GL.glGenBuffers(1)
    uvbo = GL.glGenBuffers(1)

    GL.glBindVertexArray(vao)

    # 顶点坐标缓冲
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
    GL.glBufferData(
        GL.GL_ARRAY_BUFFER,
        v_pos.nbytes,
        v_pos,
        GL.GL_DYNAMIC_DRAW
    )
    GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, 0, None)
    GL.glEnableVertexAttribArray(0)

    # UV 坐标缓冲
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, uvbo)
    GL.glBufferData(
        GL.GL_ARRAY_BUFFER,
        uv_coord.nbytes,
        uv_coord,
        GL.GL_DYNAMIC_DRAW
    )
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


class ADPOpenGLCanvas(QOpenGLWidget):

    def __init__(self):
        super().__init__()
        self.__canvas_opacity = 1.0
        self.__rotation_angle = 0.0
        # Background control
        self.__use_background = False
        self.__bg_color = (0.0, 0.0, 0.0, 0.0)
        # High-DPI handling
        self._dpr = 1.0
        self._canvas_framebuffer = None
        self._canvas_texture = None
        self._fbo_width = 0
        self._fbo_height = 0

    def __create_program(self):
        vertex_shader = """#version 330 core
        layout(location = 0) in vec2 a_position;
        layout(location = 1) in vec2 a_texCoord;

        out vec2 v_texCoord;
        uniform float rotation_angle;

        void main() {
            gl_Position = vec4(a_position, 0.0, 1.0);

            float angle = radians(rotation_angle);
            mat2 rotationMatrix = mat2(cos(angle), -sin(angle),
                                       sin(angle), cos(angle));

            vec2 centeredTexCoord = a_texCoord - vec2(0.5, 0.5);
            v_texCoord = rotationMatrix * centeredTexCoord + vec2(0.5, 0.5);
        }
        """
        frag_shader = """#version 330 core
        in vec2 v_texCoord;
        uniform sampler2D canvas;
        uniform float opacity;
        uniform vec4 bg_color;
        uniform int use_bg; // 0 or 1

        void main() {
            vec4 color = texture(canvas, v_texCoord);
            color *= opacity;
            if (use_bg == 1) {
                // Alpha composite over solid background
                vec3 rgb = mix(bg_color.rgb, color.rgb, color.a);
                gl_FragColor = vec4(rgb, 1.0);
            } else {
                gl_FragColor = color;
            }
        }
        """
        self._program = create_program(vertex_shader, frag_shader)
        self._opacity_loc = GL.glGetUniformLocation(self._program, "opacity")
        self._rotation_angle_loc = GL.glGetUniformLocation(self._program, "rotation_angle")
        self._bg_color_loc = GL.glGetUniformLocation(self._program, "bg_color")
        self._use_bg_loc = GL.glGetUniformLocation(self._program, "use_bg")

    def __create_vao(self):
        vertices = np.array([
            # 位置
            -1.0, 1.0,
            -1.0, -1.0,
            1.0, -1.0,
            -1.0, 1.0,
            1.0, -1.0,
            1.0, 1.0,
        ], dtype=np.float32)
        uvs = np.array([
            # 纹理坐标
            0.0, 1.0,
            0.0, 0.0,
            1.0, 0.0,
            0.0, 1.0,
            1.0, 0.0,
            1.0, 1.0,
        ], dtype=np.float32)
        self._vao = create_vao(vertices, uvs)

    def __delete_canvas_framebuffer(self):
        if self._canvas_texture:
            try:
                GL.glDeleteTextures([self._canvas_texture])
            except Exception:
                pass
            self._canvas_texture = None
        if self._canvas_framebuffer:
            try:
                GL.glDeleteFramebuffers(1, [self._canvas_framebuffer])
            except Exception:
                pass
            self._canvas_framebuffer = None

    def __create_canvas_framebuffer(self):
        # Determine device-pixel size for FBO
        self._dpr = float(self.devicePixelRatioF()) if hasattr(self, 'devicePixelRatioF') else float(self.devicePixelRatio())
        fb_w = max(1, int(math.ceil(self.width() * self._dpr)))
        fb_h = max(1, int(math.ceil(self.height() * self._dpr)))
        # Recreate only if size changed
        if self._canvas_framebuffer and (fb_w == self._fbo_width and fb_h == self._fbo_height):
            return
        # Delete old
        self.__delete_canvas_framebuffer()
        # Create new
        self._canvas_framebuffer, self._canvas_texture = create_canvas_framebuffer(fb_w, fb_h)
        self._fbo_width, self._fbo_height = fb_w, fb_h

    def __draw_on_canvas(self):
        # Draw model into offscreen FBO at device-pixel resolution
        old_fbo = GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._canvas_framebuffer)
        # Ensure viewport matches FBO size
        GL.glViewport(0, 0, int(self._fbo_width), int(self._fbo_height))
        # Keep FBO transparent so compositing in second pass works
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.on_draw()
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, old_fbo)

    def initializeGL(self):
        self.__create_program()
        self.__create_vao()
        self.__create_canvas_framebuffer()
        self.on_init()
        # Ensure model has correct initial size in pixels
        self.on_resize(self._fbo_width, self._fbo_height)

    def resizeGL(self, w, h):
        # Recreate FBO when widget size or DPR changes
        old_dpr = self._dpr
        self._dpr = float(self.devicePixelRatioF()) if hasattr(self, 'devicePixelRatioF') else float(self.devicePixelRatio())
        if (int(math.ceil(w * self._dpr)) != self._fbo_width) or (int(math.ceil(h * self._dpr)) != self._fbo_height) or (self._dpr != old_dpr):
            self.__create_canvas_framebuffer()
        # Notify subclass with pixel sizes
        self.on_resize(self._fbo_width, self._fbo_height)

    def paintGL(self):
        # First render to offscreen canvas
        self.__draw_on_canvas()
        # Then draw the canvas texture to the widget's default framebuffer
        # Clear to transparent; background color compositing is handled in shader
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        # Ensure viewport matches default framebuffer size in pixels (HiDPI safe)
        dpr = float(self.devicePixelRatioF()) if hasattr(self, 'devicePixelRatioF') else float(self.devicePixelRatio())
        vp_w = max(1, int(round(self.width() * dpr)))
        vp_h = max(1, int(round(self.height() * dpr)))
        GL.glViewport(0, 0, vp_w, vp_h)

        GL.glBindVertexArray(self._vao)
        GL.glUseProgram(self._program)

        GL.glProgramUniform1f(self._program, self._opacity_loc, self.__canvas_opacity)
        GL.glProgramUniform1f(self._program, self._rotation_angle_loc, self.__rotation_angle)
        GL.glProgramUniform4f(self._program, self._bg_color_loc, *self.__bg_color)
        GL.glProgramUniform1i(self._program, self._use_bg_loc, 1 if self.__use_background else 0)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._canvas_texture)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

        GL.glBindVertexArray(0)

    def setCanvasOpacity(self, value):
        self.__canvas_opacity = value
        self.update()

    def setRotationAngle(self, angle):
        self.__rotation_angle = float(angle)
        self.update()

    def setBackground(self, transparent: bool, qcolor):
        """Configure background compositing.
        If transparent is True, the widget remains transparent.
        Otherwise, fill with the provided QColor.
        """
        self.__use_background = not bool(transparent)
        if qcolor is not None:
            # QColor -> normalized RGBA
            r, g, b, a = qcolor.redF(), qcolor.greenF(), qcolor.blueF(), 1.0
            self.__bg_color = (r, g, b, a)
        else:
            self.__bg_color = (0.0, 0.0, 0.0, 1.0)
        self.update()

    # Advanced params API
    def setAdvancedParams(self, enabled: bool, params: dict):
        self._advanced_enabled = bool(enabled)
        self._advanced_params = dict(params) if params else {}
        # Apply immediately using SetParameterValue when available
        if self._advanced_enabled and self._advanced_params and self.model is not None:
            set_val = getattr(self.model, "SetParameterValue", None)
            if callable(set_val):
                for pid, v in self._advanced_params.items():
                    try:
                        set_val(pid, float(v))
                    except Exception:
                        continue
        self.update()

    def _apply_advanced_params(self):
        m = self.model
        if m is None or not self._advanced_params:
            return
        set_val = getattr(m, "SetParameterValue", None)
        if not callable(set_val):
            # If API not available, do nothing to honor request of using SetParameterValue
            return
        for pid, v in self._advanced_params.items():
            try:
                set_val(pid, float(v))
            except Exception:
                continue

    @abstractmethod
    def on_init(self):
        pass

    @abstractmethod
    def on_draw(self):
        pass

    @abstractmethod
    def on_resize(self, width: int, height: int):
        pass



class Live2DCanvas(ADPOpenGLCanvas):
    def __init__(self, model_path = None):
        super().__init__()
        self.model_path = model_path
        self.model: Optional[live2d.LAppModel] = None
        # tool for controlling model opacity
        self.canvas: Optional[Canvas] = None
        self.setWindowTitle("Live2DCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.radius_per_frame = math.pi * 0.5 / 120
        self.total_radius = 0
        # Mouse follow control
        self._mouse_follow_enabled = False
        # Advanced parameter overrides
        self._advanced_enabled = False
        self._advanced_params = {}
        # Cached motions metadata
        self._motions: List[Dict[str, Any]] = []

    def on_init(self):
        live2d.glInit()
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(self.model_path)
        # must be created after opengl context is configured
        self.canvas = Canvas()
        # Discover motions from model json
        try:
            self._motions = self._load_motions_from_model_json(self.model_path)
        except Exception:
            self._motions = []
        self.startTimer(int(1000 / 120))

    def timerEvent(self, a0):
        self.update()

    def on_draw(self):
        live2d.clearBuffer()
        self.model.Update()
        # Apply advanced parameter overrides each frame if enabled
        if self._advanced_enabled:
            try:
                self._apply_advanced_params()
            except Exception:
                pass
        self.model.Draw()

    def on_resize(self, width: int, height: int):
        self.model.Resize(width, height)

    # --- Mouse tracking and follow implementation ---
    def setMouseTracking(self, enable: bool) -> None:  # type: ignore[override]
        super().setMouseTracking(bool(enable))
        self._mouse_follow_enabled = bool(enable)

    def mouseMoveEvent(self, event):
        if not self._mouse_follow_enabled or self.model is None:
            return super().mouseMoveEvent(event)
        w = max(1, self.width())
        h = max(1, self.height())
        px = event.pos().x()
        py = event.pos().y()
        # Normalize to [-1, 1], origin center, +x right, +y up
        nx = (px / w - 0.5) * 2.0
        ny = (0.5 - py / h) * 2.0
        self._apply_mouse_follow(nx, ny)
        self.update()
        return super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        # Reset follow when cursor leaves
        if self._mouse_follow_enabled and self.model is not None:
            try:
                self._apply_mouse_follow(0.0, 0.0)
            except Exception:
                pass
        return super().leaveEvent(event)

    def _apply_mouse_follow(self, nx: float, ny: float):
        """Try multiple strategies to apply mouse-follow to the model.
        nx/ny: normalized [-1, 1].
        Priority: SetDrag/SetDragging; fallback to parameter setting.
        """
        m = self.model
        if m is None:
            return
        # Preferred API used by many LAppModel wrappers
        for name in ("SetDrag", "SetDragging", "SetMouse"):
            fn = getattr(m, name, None)
            if callable(fn):
                try:
                    fn(float(nx), float(ny))
                    return
                except Exception:
                    pass
        # Fallback: set common parameter IDs
        angle_x = float(max(-1.0, min(1.0, nx))) * 30.0
        angle_y = float(max(-1.0, min(1.0, ny))) * 30.0
        body_x = float(max(-1.0, min(1.0, nx))) * 10.0
        eye_x = float(max(-1.0, min(1.0, nx)))
        eye_y = float(max(-1.0, min(1.0, ny)))
        # Candidate setter names in different wrappers
        setter_candidates = [
            "SetParamFloat", "SetParameterFloat", "SetParameterValue", "SetParameter",
        ]
        def try_set(param_id: str, value: float):
            for s in setter_candidates:
                fn = getattr(m, s, None)
                if callable(fn):
                    try:
                        fn(param_id, float(value))
                        return True
                    except Exception:
                        continue
            return False
        # Apply a few representative parameters (best-effort)
        try_set("ParamAngleX", angle_x)
        try_set("ParamAngleY", angle_y)
        try_set("ParamBodyAngleX", body_x)
        try_set("ParamEyeBallX", eye_x)
        try_set("ParamEyeBallY", eye_y)

    def setAutoBlinkEnable(self, enabled: bool):
        try:
            if self.model:
                self.model.SetAutoBlinkEnable(bool(enabled))
        except Exception:
            pass

    def setAutoBreathEnable(self, enabled: bool):
        try:
            if self.model:
                self.model.SetAutoBreathEnable(bool(enabled))
        except Exception:
            pass

    def release(self):
        """Release the current model and GL resources"""
        if self.model is not None:
            try:
                self.model = None
            except Exception as e:
                print(f"Error releasing model: {e}")
        # Delete FBO/texture
        try:
            self._ADPOpenGLCanvas__delete_canvas_framebuffer()
        except Exception:
            pass

    def getParameterMetaList(self):
        """Return a list of parameter metadata from the loaded model.
        Each item: { 'id': str, 'type': any, 'value': float, 'min': float, 'max': float, 'default': float }
        Returns empty list if model is not ready or API not available.
        """
        m = self.model
        meta = []
        try:
            if m is None:
                return meta
            count_attr = getattr(m, 'GetParameterCount', None)
            getter = getattr(m, 'GetParameter', None)
            if not callable(getter):
                return meta
            if callable(count_attr):
                n = int(count_attr())
            else:
                try:
                    n = int(count_attr or 0)
                except Exception:
                    n = 0
            for i in range(n):
                try:
                    p = getter(i)
                    pid = getattr(p, 'id', None)
                    ptype = getattr(p, 'type', None)
                    pval = float(getattr(p, 'value', 0.0))
                    pmax = float(getattr(p, 'max', 1.0))
                    pmin = float(getattr(p, 'min', 0.0))
                    pdef = float(getattr(p, 'default', 0.0))
                    if pid is None:
                        continue
                    meta.append({
                        'id': str(pid),
                        'type': ptype,
                        'value': pval,
                        'min': pmin,
                        'max': pmax,
                        'default': pdef,
                    })
                except Exception:
                    continue
        except Exception:
            return []
        return meta

    # --- Motion discovery and playback helpers ---
    def _load_motions_from_model_json(self, model_json_path: str) -> List[Dict[str, Any]]:
        """Parse the model3.json file to discover motion groups and files.
        Returns a list of items: { 'group': str, 'index': int, 'file': str, 'display': str }
        """
        import os
        import json
        motions: List[Dict[str, Any]] = []
        if not model_json_path:
            return motions
        base_dir = os.path.dirname(model_json_path)
        try:
            with open(model_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return motions
        refs = (data or {}).get('FileReferences') or {}
        motion_groups = refs.get('Motions') or {}
        for group, items in motion_groups.items():
            if not isinstance(items, list):
                continue
            for idx, it in enumerate(items):
                if not isinstance(it, dict):
                    continue
                rel = it.get('File') or ''
                if not rel:
                    continue
                full_path = os.path.normpath(os.path.join(base_dir, rel))
                display = f"{group}[{idx}] - {os.path.basename(rel)}"
                motions.append({
                    'group': str(group),
                    'index': int(idx),
                    'file': full_path,
                    'rel': rel,
                    'display': display,
                })
        return motions

    def listMotions(self) -> List[Dict[str, Any]]:
        """Return cached motion list. Safe to call before GL init (may be empty)."""
        return list(self._motions or [])

    def playMotion(self, group: str, index: int) -> bool:
        """Try to play a motion by group/index using best-effort API calls.
        Returns True if a call was attempted successfully.
        """
        m = self.model
        if m is None:
            return False
        # Try common LAppModel APIs
        candidates = [
            ('StartMotion', (group, int(index), 1)),
            ('StartMotionPriority', (group, int(index), 1)),
            ('StartMotion', (group, int(index))),
        ]
        for name, args in candidates:
            fn = getattr(m, name, None)
            if callable(fn):
                try:
                    fn(*args)
                    return True
                except Exception:
                    continue
        # Fallback by file path if supported
        file_item = None
        for it in self._motions:
            if it.get('group') == group and int(it.get('index', -1)) == int(index):
                file_item = it
                break
        if file_item is not None:
            for name in (
                'StartMotionByFile', 'StartMotionFromFile', 'StartMotionFile', 'PlayMotion', 'LoadAndStartMotion'
            ):
                fn = getattr(m, name, None)
                if callable(fn):
                    try:
                        fn(file_item['file'])
                        return True
                    except Exception:
                        continue
        # As a last resort, try random motion in the group
        rnd = getattr(m, 'StartRandomMotion', None)
        if callable(rnd):
            try:
                rnd(group, 1)
                return True
            except Exception:
                pass
        return False
