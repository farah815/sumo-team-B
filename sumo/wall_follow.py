from geometry_msgs.msg import Twist

def get_wall_follow_twist(front_dist, right_dist, target_distance, prev_error, dt, kp, kd):
    """
    يُطبق تحكم PD مع نظام أمان (Anti-Crash) يتراجع للخلف إذا اقترب الروبوت بشدة من الجدار.
    """
    twist = Twist()
    safe_front_dist = 0.40  # مسافة التوقف الأمامي الآمنة
    safe_right_dist = 0.18  # المسافة الحرجة لو اقترب الروبوت يميناً زيادة عن اللزوم
    lost_wall = False
    
    # 1. حماية فقدان الجدار (لو فجأة مفيش حيطة على اليمين)
    if right_dist > 1.5:
        lost_wall = True
        return twist, 0.0, lost_wall
        
    # 2. 🚨 نظام حماية الاصطدام والالتصاق (Anti-Crash & Reverse)
    if front_dist < safe_front_dist or right_dist < safe_right_dist:
        # بدلاً من الالتصاق والتحطم: الروبوت سيتراجع للخلف ويدور لليسار للهروب بأمان!
        twist.linear.x = -0.15  # تراجع للخلف ببطء
        twist.angular.z = 1.2   # دوران قوي لليسار للابتعاد عن الحائط
        new_error = 0.0
    
    # 3. تتبع الجدار الطبيعي والآمن
    else:
        error = target_distance - right_dist
        
        # حساب التفاضل الزمني
        derivative = (error - prev_error) / dt if dt > 0 else 0.0
        steering = (kp * error) + (kd * derivative)
        
        # سرعة هادئة وثابتة لتجنب الصدمات
        speed = 0.2 * (1.0 - min(abs(error), 1.0))
        twist.linear.x = max(0.05, speed)  # سرعة بطيئة وآمنة
        
        # تحجيم الدوران (Clamp) لمنع الحركة العنيفة
        twist.angular.z = max(min(steering, 1.0), -1.0)
        new_error = error
        
    return twist, new_error, lost_wall