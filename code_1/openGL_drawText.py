'''
Created on 2023/12/28

@author: AD2Gen2-19
'''
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
import freetype
import glm
import numpy as np

fontfile = "res/font/consola.ttf"

class CharacterSlot:
    def __init__(self, texture, glyph):
        self.texture = texture
        self.textureSize = (glyph.bitmap.width, glyph.bitmap.rows)

        if isinstance(glyph, freetype.GlyphSlot):
            self.bearing = (glyph.bitmap_left, glyph.bitmap_top)
            self.advance = glyph.advance.x
        elif isinstance(glyph, freetype.BitmapGlyph):
            self.bearing = (glyph.left, glyph.top)
            self.advance = None
        else:
            raise RuntimeError('unknown glyph type')

def _get_rendering_buffer(xpos, ypos, w, h, zfix=0.0):
    return np.asarray([
        xpos,     ypos - h, 0, 0,
        xpos,     ypos,     0, 1,
        xpos + w, ypos,     1, 1,
        xpos,     ypos - h, 0, 0,
        xpos + w, ypos,     1, 1,
        xpos + w, ypos - h, 1, 0
    ], np.float32)

VERTEX_SHADER = """
        #version 330 core
        layout (location = 0) in vec4 vertex; // <vec2 pos, vec2 tex>
        out vec2 TexCoords;

        uniform mat4 projection;

        void main()
        {
            gl_Position = projection * vec4(vertex.xy, 0.0, 1.0);
            TexCoords = vertex.zw;
        }
       """

FRAGMENT_SHADER = """
        #version 330 core
        in vec2 TexCoords;
        out vec4 color;

        uniform sampler2D text;
        uniform vec3 textColor;

        void main()
        {    
            vec4 sampled = vec4(1.0, 1.0, 1.0, texture(text, TexCoords).r);
            color = vec4(textColor, 1.0) * sampled;
        }
        """

shaderProgram = None
Characters = dict()
VBO = None
VAO = None

def textinitliaze():
    global VERTEXT_SHADER
    global FRAGMENT_SHADER
    global shaderProgram
    global Characters
    global VBO
    global VAO

    #compiling shaders
    vertexshader = shaders.compileShader(VERTEX_SHADER, GL_VERTEX_SHADER)
    fragmentshader = shaders.compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
# 
#     #creating shaderProgram
    shaderProgram = shaders.compileProgram(vertexshader, fragmentshader)
#     glUseProgram(shaderProgram)

    #get projection
    #problem
    
#     shader_projection = glGetUniformLocation(shaderProgram, "projection")
#     projection = glm.ortho(0, W_INIT, H_INIT, 0)
#     glUniformMatrix4fv(shader_projection, 1, GL_FALSE, glm.value_ptr(projection))
    
    #disable byte-alignment restriction
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    face = freetype.Face(fontfile)
    face.set_char_size( 48*64 )

    #load first 128 characters of ASCII set
    for i in range(0,128):
        face.load_char(chr(i))
        glyph = face.glyph
        
        #generate texture
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, glyph.bitmap.width, glyph.bitmap.rows, 0,
                     GL_RED, GL_UNSIGNED_BYTE, glyph.bitmap.buffer)

        #texture options
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        #now store character for later use
        Characters[chr(i)] = CharacterSlot(texture,glyph)
#         
    glBindTexture(GL_TEXTURE_2D, 0)
  
    #configure VAO/VBO for texture quads
    VAO = glGenVertexArrays(1)
    glBindVertexArray(VAO)
      
    VBO = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, 6 * 4 * 4, None, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

def render_text_start(width, height):
    global shaderProgram
    global Characters
    global VBO
    global VAO
    
    glUseProgram(shaderProgram)
     
    shader_projection = glGetUniformLocation(shaderProgram, "projection")
    projection = glm.ortho(0, width, height, 0)
    glUniformMatrix4fv(shader_projection, 1, GL_FALSE, glm.value_ptr(projection))
     
    face = freetype.Face(fontfile)
    face.set_char_size(48*64)
    
    glActiveTexture(GL_TEXTURE0)
     
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
 
    glBindVertexArray(VAO)
    
def render_text(text, x, y, scale, color):
    global shaderProgram
    global Characters
    global VBO
    global VAO
    
    glUniform3f(glGetUniformLocation(shaderProgram, "textColor"), color[0], color[1], color[2])
    
    for c in text:
        if not c in Characters:
            ch = Characters[' ']
        else:
            ch = Characters[c]
        w, h = ch.textureSize
        w = w*scale
        h = h*scale
        vertices = _get_rendering_buffer(x,y,w,h)

        #render glyph texture over quad
        glBindTexture(GL_TEXTURE_2D, ch.texture)
        #update content of VBO memory
        glBindBuffer(GL_ARRAY_BUFFER, VBO)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        #render quad
        glDrawArrays(GL_TRIANGLES, 0, 6)
        #now advance cursors for next glyph (note that advance is number of 1/64 pixels)
        x += (ch.advance>>6)*scale
 
def render_text_end():
    glBindVertexArray(0)
    
    glBindTexture(GL_TEXTURE_2D, 0)
     
    glDisable(GL_BLEND)
    glUseProgram(0)