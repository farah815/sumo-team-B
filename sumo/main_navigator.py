import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Imu
from geometry_msgs.msg import Twist
import math

class PerfectSumoNavigator(Node):
    def __init__(self):
        super().__init__('perfect_sumo_navigator')
        
        self.get_logger().info('Smart Sumo Navigator IMU Memory Initialized! Waiting for Lidar...')
        
        self.subscription_scan = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.subscription_imu = self.create_subscription(
            Imu, '/imu', self.imu_callback, 10)
        
        self.publisher_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.current_yaw = 0.0
        self.target_yaw = 0.0
        
        self.front_dist = 3.0
        self.back_dist = 3.0
        self.left_dist = 3.0
        self.right_dist = 3.0
        
        self.prev_left_dist = 3.0
        self.prev_right_dist = 3.0
        
        self.scan_received = False
        
        self.state = 'FORWARD'
        self.clearing_ticks = 0
        self.side_advance_ticks = 0 
        
        self.open_space_counter = 0
        self.startup_counter = 0
        
        self.timer = self.create_timer(0.1, self.control_loop)

    def imu_callback(self, msg):
        orientation_q = msg.orientation
        siny_cosp = 2.0 * (orientation_q.w * orientation_q.z + orientation_q.x * orientation_q.y)
        cosy_cosp = 1.0 - 2.0 * (orientation_q.y * orientation_q.y + orientation_q.z * orientation_q.z)
        self.current_yaw = math.atan2(siny_cosp, cosy_cosp)

    def scan_callback(self, msg):
        ranges = msg.ranges
        if not ranges:
            return
        
        n = len(ranges)
        quarter = n // 4
        half = n // 2
        three_quarter = 3 * quarter

        back_indices = list(range(0, 15)) + list(range(n - 15, n))
        right_indices = range(quarter - 15, quarter + 15)
        front_indices = range(half - 15, half + 15)
        left_indices = range(three_quarter - 15, three_quarter + 15)
        
        back_ranges = [ranges[i] for i in back_indices if 0 <= i < n and not math.isinf(ranges[i]) and not math.isnan(ranges[i])]
        right_ranges = [ranges[i] for i in right_indices if 0 <= i < n and not math.isinf(ranges[i]) and not math.isnan(ranges[i])]
        front_ranges = [ranges[i] for i in front_indices if 0 <= i < n and not math.isinf(ranges[i]) and not math.isnan(ranges[i])]
        left_ranges = [ranges[i] for i in left_indices if 0 <= i < n and not math.isinf(ranges[i]) and not math.isnan(ranges[i])]
        
        self.prev_left_dist = self.left_dist
        self.prev_right_dist = self.right_dist

        self.back_dist = min(back_ranges) if back_ranges else float('inf')
        self.right_dist = min(right_ranges) if right_ranges else float('inf')
        self.front_dist = min(front_ranges) if front_ranges else float('inf')
        self.left_dist = min(left_ranges) if left_ranges else float('inf')

        self.scan_received = True

    def control_loop(self):
        if not self.scan_received:
            return

        twist = Twist()


        if self.state == 'ADVANCING_SIDE':
            twist.linear.x = 0.5
            twist.angular.z = 0.0
            self.side_advance_ticks -= 1
            

            if self.front_dist < 0.4 or self.side_advance_ticks <= 0:
                self.get_logger().info("[ADVANCE DONE] Cleared corner. Now spinning...")
                self.state = 'TURNING'

        elif self.state == 'TURNING':
            twist.linear.x = 0.0
            yaw_error = self.target_yaw - self.current_yaw
            yaw_error = math.atan2(math.sin(yaw_error), math.cos(yaw_error))
            
            if abs(yaw_error) < 0.08:
                self.get_logger().info(f"[TURN COMPLETE] Aligned. Moving forward blindly to clear junction.")
                self.state = 'CLEARING'
                self.clearing_ticks = 10
            else:
                twist.angular.z = max(-3.0, min(3.0, 4.0 * yaw_error))

        elif self.state == 'CLEARING':
            twist.linear.x = 0.8
            twist.angular.z = 0.0
            self.clearing_ticks -= 1
            if self.clearing_ticks <= 0:
                self.get_logger().info(f"[CLEARING DONE] Junction passed. Resuming normal logic.")
                self.state = 'FORWARD'

        elif self.state == 'FORWARD':

            if self.startup_counter < 30:
                self.startup_counter += 1
            else:
                is_arena_open = (
                    (math.isinf(self.front_dist) or self.front_dist > 6.0) and
                    (math.isinf(self.back_dist) or self.back_dist > 6.0) and
                    (math.isinf(self.left_dist) or self.left_dist > 6.0) and
                    (math.isinf(self.right_dist) or self.right_dist > 6.0)
                )
                
                if is_arena_open:
                    self.open_space_counter += 1

                    if self.open_space_counter > 15:
                        twist.linear.x = 0.0
                        twist.angular.z = 0.0
                        self.publisher_cmd.publish(twist)
                        self.get_logger().info(f"[SUCCESS] Robot strictly reached the real Arena and stopped safely!")
                        self.state = 'STOPPED'
                        return
                else:
                    self.open_space_counter = 0

            is_front_blocked = self.front_dist < 0.5
            is_left_opening_suddenly = (self.prev_left_dist < 1.0) and (self.left_dist > 2.0)
            is_right_opening_suddenly = (self.prev_right_dist < 1.0) and (self.right_dist > 2.0)
            is_side_opened = is_left_opening_suddenly or is_right_opening_suddenly

            if is_front_blocked or is_side_opened:

                twist.linear.x = 0.0
                
                relative_dirs = {
                    'front': (self.front_dist, 0.0, 0),
                    'left': (self.left_dist, math.pi / 2, 90),
                    'back': (self.back_dist, math.pi, 180),
                    'right': (self.right_dist, -math.pi / 2, -90)
                }
                
                valid_choices = {}
                for d_name, (d_val, d_angle_offset, d_deg) in relative_dirs.items():
                    if d_name == 'front' and d_val < 0.35:
                        continue
                    
                    if d_val > 0.4:
                        abs_choice_yaw = self.current_yaw + d_angle_offset
                        abs_choice_yaw = math.atan2(math.sin(abs_choice_yaw), math.cos(abs_choice_yaw))
                        
                        if hasattr(self, 'banned_yaw'):
                            yaw_diff = abs_choice_yaw - self.banned_yaw
                            yaw_diff = math.atan2(math.sin(yaw_diff), math.cos(yaw_diff))
                            if abs(yaw_diff) < 0.5:
                                continue
                                
                        valid_choices[d_name] = (d_val, d_angle_offset, d_deg)
                
                if valid_choices:
                    if 'front' in valid_choices and valid_choices['front'][0] > 0.8 and not is_side_opened:
                        twist.linear.x = 0.8
                        twist.angular.z = 0.0
                        self.publisher_cmd.publish(twist)
                        return
                    else:
                        side_choices = {k: v for k, v in valid_choices.items() if k != 'back'}
                        if side_choices:
                            best_dir_name, (best_dist, best_offset, best_deg) = max(side_choices.items(), key=lambda item: item[1][0])
                        else:
                            best_dir_name, (best_dist, best_offset, best_deg) = max(valid_choices.items(), key=lambda item: item[1][0])
                else:
                    best_dir_name, (best_dist, best_offset, best_deg) = max(relative_dirs.items(), key=lambda item: item[1][0])

                self.target_yaw = self.current_yaw + best_offset
                self.target_yaw = math.atan2(math.sin(self.target_yaw), math.cos(self.target_yaw))
                
                self.banned_yaw = self.target_yaw + math.pi
                self.banned_yaw = math.atan2(math.sin(self.banned_yaw), math.cos(self.banned_yaw))
                
                self.get_logger().info(f">> DECISION: Chosen [{best_dir_name.upper()}] with Distance: {best_dist:.2f}m | Angle: {best_deg}°")

                if abs(best_offset) < 0.1:
                    self.state = 'CLEARING'
                    self.clearing_ticks = 10
                else:

                    if is_side_opened and not is_front_blocked and self.front_dist > 0.6:
                        self.state = 'ADVANCING_SIDE'
                        self.side_advance_ticks = 5  
                    else:
                        self.state = 'TURNING'
            else:
                twist.linear.x = 0.8
                twist.angular.z = 0.0

        elif self.state == 'STOPPED':
            twist.linear.x = 0.0
            twist.angular.z = 0.0
                
        self.publisher_cmd.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = PerfectSumoNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()