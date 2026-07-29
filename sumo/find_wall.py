from geometry_msgs.msg import Twist

def get_find_wall_twist(right_dist, target_distance):
    """
    نمط البحث: التقدم للأمام مع دوران تدريجي (Spiral) 
    حتى يلتقط الليدار جداراً على يمينه.
    """
    twist = Twist()
    wall_found = False
    
    # إذا كان الجدار بعيداً جداً، استمر في البحث
    if right_dist > (target_distance + 0.3):
        twist.linear.x = 0.2
        twist.angular.z = -0.3  # انحراف دائري هادئ لليمين
    else:
        # تم العثور على الجدار
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        wall_found = True
        
    return twist, wall_found