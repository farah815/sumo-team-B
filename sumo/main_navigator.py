import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy
import math

class PerfectSumoNavigator(Node):
    def __init__(self):
        super().__init__('perfect_sumo_navigator')
        
        qos_profile = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)      
        self.pub_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub_scan = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_profile)
        
        self.timer = self.create_timer(0.1, self.control_loop)
        
        self.front_dist = 999.0
        self.right_dist = 999.0
        self.scan_received = False
        
        self.target_dist = 0.45
        self.prev_angular_z = 0.0
        
        self.get_logger().info("Perfect Non-Reversing Sumo Navigator Initialized!")

    def scan_callback(self, msg: LaserScan):
        self.scan_received = True
        front_rays, right_rays = [], []
        
        for i, r in enumerate(msg.ranges): #check each ray
            if math.isinf(r) or math.isnan(r) or r < 0.20:   # if laser reading inf/nan/lessthan 0.2
                continue #ignore
                
            angle_rad = msg.angle_min + (i * msg.angle_increment) # angle of rays
            deg = math.degrees(angle_rad) 
            deg = (deg + 180) % 360 - 180
            
            if -35 <= deg <= 35: 
                front_rays.append(r)
            elif -120 <= deg <= -60: 
                right_rays.append(r)
                
        self.front_dist = min(front_rays) if front_rays else 999.0
        self.right_dist = min(right_rays) if right_rays else 999.0

    def control_loop(self):
        if not self.scan_received:
            return

        raw_angular_z = 0.0
        linear_x = 0.35
        action = ""

    
        if self.front_dist < 0.55:
            linear_x = 0.0
            raw_angular_z = 1.3
            action = "🛑 CORNER: Turning in place (No Reversing)"
            
        elif self.right_dist > 1.5:
            linear_x = 0.25
            raw_angular_z = -0.3
            action = "🔍 SEARCHING WALL"
            
        elif self.right_dist < 0.32:
            linear_x = 0.3
            raw_angular_z = 0.5
            action = " TOO CLOSE: Avoiding"
            
        else: #everything is normal 
            error = self.right_dist - self.target_dist  #positive means far away negative means too close
            linear_x = 0.35
            raw_angular_z = -1.2 * error
            action = "RUISING SMOOTHLY"

        # عامل التخميد لمنع الهز يمين وشمال وجعل الحركة ناعمة
        alpha = 0.4  
        smoothed_angular_z = alpha * raw_angular_z + (1.0 - alpha) * self.prev_angular_z
        self.prev_angular_z = smoothed_angular_z

        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = smoothed_angular_z

        self.pub_vel.publish(twist)
        self.get_logger().info(f"Action: {action} | Linear: {linear_x:.2f} | Angular: {smoothed_angular_z:.2f}")

def main():
    rclpy.init()
    node = PerfectSumoNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()