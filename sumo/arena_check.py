def is_open_space(front_dist, right_dist, left_dist, threshold=2.0):
    """
    يتحقق مما إذا كانت جميع الاتجاهات مفتوحة أكبر من مسافة معينة.
    يُرجع True إذا كانت المساحة واسعة، و False إذا كان هناك أي جدار.
    """
    return (front_dist > threshold and right_dist > threshold and left_dist > threshold)