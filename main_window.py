import arcade
import pymunk
import cv2
import random
import timeit
import math
from PIL import Image
import numpy as np

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = ""


class Camera():
    def __init__(self):
        self.capture = cv2.VideoCapture(0)
        self.count = 0

    def update(self):
        self.sprite = arcade.Sprite()
        self.sprite.position = (1050, 360)
        ret, frame_image_cv = self.capture.read()
        frame_image_cv = cv2.resize(frame_image_cv, (320, 180))
        frame_image_cv = cv2.cvtColor(frame_image_cv, cv2.COLOR_RGB2RGBA)

        # HSV変換
        hsv = cv2.cvtColor(frame_image_cv, cv2.COLOR_BGR2HSV)
        # 2値化
        bin_img = ~cv2.inRange(hsv, (62, 100, 0), (79, 255, 255))
        # 輪郭抽出
        contours = cv2.findContours(
            bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]
        # 面積が最大の輪郭を取得
        contour = max(contours, key=lambda x: cv2.contourArea(x))
        # マスク画像作成
        mask = np.zeros_like(bin_img)
        cv2.drawContours(mask, [contour], -1, color=255, thickness=-1)
        # 幅、高さは前景画像と背景画像の共通部分をとる
        w = frame_image_cv.shape[1]
        h = frame_image_cv.shape[0]
        # 合成する領域
        fg_roi = frame_image_cv[:h, :w]
        bg_roi = np.zeros((h, w, 4), np.uint8)
        # 合成
        frame_image_cv = np.where(
            mask[:h, :w, np.newaxis] == 0, bg_roi, fg_roi)

        frame_img_pil = cv2pil(frame_image_cv)
        self.sprite.texture = arcade.Texture(
            name=f"{self.count}", image=frame_img_pil, hit_box_algorithm="Detailed")

    def draw(self):
        self.sprite.draw()

    def get_sprite(self):
        # print(self.sprite.texture.hit_box_points)
        self.count += 1
        return self.sprite


def cv2pil(image):
    # OpenCV型 -> PIL型
    new_image = image.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


class CircleSprite(arcade.Sprite):
    def __init__(self, filename, pymunk_shape):
        super().__init__(filename, center_x=pymunk_shape.body.position.x,
                         center_y=pymunk_shape.body.position.y)
        self.width = pymunk_shape.radius * 2
        self.height = pymunk_shape.radius * 2
        self.pymunk_shape = pymunk_shape


class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self, width, height, title):
        super().__init__(width, height, title)
        self.set_update_rate(1/1000)

        self.peg_list = arcade.SpriteList()
        self.ball_list: arcade.SpriteList[CircleSprite] = arcade.SpriteList()
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)

        self.draw_time = 0
        self.delta_time = 0
        self.time = 0

        # -- Camera
        self.camera = Camera()
        self.camera.update()

        # -- Pymunk
        self.space = pymunk.Space()
        self.space.gravity = (0.0, -900.0)

        self.static_lines = []

        self.ticks_to_next_ball = 10

        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        shape = pymunk.Segment(body, [0, 10], [SCREEN_WIDTH, 10], 0.0)
        shape.friction = 10
        self.space.add(body, shape)
        self.static_lines.append(shape)

        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        shape = pymunk.Segment(
            body, [SCREEN_WIDTH - 50, 10], [SCREEN_WIDTH, 30], 0.0)
        shape.friction = 10
        self.space.add(body, shape)
        self.static_lines.append(shape)

        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        shape = pymunk.Segment(body, [50, 10], [0, 30], 0.0)
        shape.friction = 10
        self.space.add(body, shape)
        self.static_lines.append(shape)

        radius = 20
        separation = 150
        for row in range(6):
            for column in range(6):
                x = column * separation + (separation // 2 * (row % 2))
                y = row * separation + separation // 2
                body = pymunk.Body(body_type=pymunk.Body.STATIC)
                body.position = x, y
                shape = pymunk.Circle(body, radius, pymunk.Vec2d(0, 0))
                shape.friction = 0.3
                self.space.add(body, shape)

                sprite = CircleSprite(
                    ":resources:images/pinball/bumper.png", shape)
                self.peg_list.append(sprite)

    def on_draw(self):
        """
        Render the screen.
        """

        # This command has to happen before we start drawing
        arcade.start_render()

        draw_start_time = timeit.default_timer()
        self.peg_list.draw()
        self.ball_list.draw()

        for line in self.static_lines:
            body = line.body

            pv1 = body.position + line.a.rotated(body.angle)
            pv2 = body.position + line.b.rotated(body.angle)
            arcade.draw_line(pv1.x, pv1.y, pv2.x, pv2.y, arcade.color.WHITE, 2)

        """
        # Display timings
        output = f"FPS: {1//self.delta_time}"
        arcade.draw_text(output, 20, SCREEN_HEIGHT -
                         20, arcade.color.WHITE, 12)

        output = f"Drawing time: {self.draw_time:.3f}"
        arcade.draw_text(output, 20, SCREEN_HEIGHT -
                         40, arcade.color.WHITE, 12)
        """

        # Draw hit box
        for ball in self.ball_list:
            ball.draw_hit_box(arcade.color.RED, 3)

        # Camera
        self.camera.draw()

        self.draw_time = timeit.default_timer() - draw_start_time

    def on_update(self, delta_time):
        start_time = timeit.default_timer()

        self.ticks_to_next_ball -= 1
        if self.ticks_to_next_ball <= 0:
            self.ticks_to_next_ball = 20
            mass = 0.5
            radius = 15
            inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))
            body = pymunk.Body(mass, inertia)
            x = random.randint(0, SCREEN_WIDTH)
            y = SCREEN_HEIGHT
            body.position = x, y
            shape = pymunk.Circle(body, radius, pymunk.Vec2d(0, 0))
            shape.friction = 0.3
            self.space.add(body, shape)

            sprite = CircleSprite(":resources:images/items/gold_1.png", shape)
            self.ball_list.append(sprite)

        # Check for balls that fall off the screen
        for ball in self.ball_list:
            if ball.pymunk_shape.body.position.y < 0:
                # Remove balls from physics space
                self.space.remove(ball.pymunk_shape, ball.pymunk_shape.body)
                # Remove balls from physics list
                ball.remove_from_sprite_lists()

        # Update physics
        # Use a constant time step, don't use delta_time
        # See "Game loop / moving time forward"
        # http://www.pymunk.org/en/latest/overview.html#game-loop-moving-time-forward
        self.space.step(1 / 60.0)

        # Move sprites to where physics objects are
        for ball in self.ball_list:
            ball.center_x = ball.pymunk_shape.body.position.x
            ball.center_y = ball.pymunk_shape.body.position.y
            ball.angle = math.degrees(ball.pymunk_shape.body.angle)

        # Camera
        self.camera.update()

        self.time = timeit.default_timer() - start_time
        self.delta_time = delta_time

    def on_key_press(self, key, modifiers):
        if key == arcade.key.P:
            self.generate_sprite(self.camera.get_sprite())

    def generate_sprite(self, sprite):
        mass = 0.5
        radius = 15
        inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))
        body = pymunk.Body(mass, inertia)
        x = random.randint(0, SCREEN_WIDTH)
        y = SCREEN_HEIGHT
        body.position = x, y
        shape = pymunk.Poly(body, sprite.texture.hit_box_points)
        shape.friction = 0.3
        self.space.add(body, shape)
        sprite.pymunk_shape = shape
        self.ball_list.append(sprite)


def main():
    MyGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    arcade.run()


if __name__ == "__main__":
    main()
