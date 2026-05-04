from django.apps import AppConfig


class InspectionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inspections'
    verbose_name = 'التقييمات'

    def get_evaluation_action(self, score: float) -> str:
        """
        Returns the action based on the evaluation score percentage.
        - 0% – 40%: ضعيف، إيقاف الإنتاج
        - 41% – 69%: مقبول، يحتاج تأهيل ومزيد من التحسين، يتحول مباشرة للتأهيل
        """
        if 0 <= score <= 40:
            return "ضعيف، إيقاف الإنتاج"
        elif 41 <= score <= 69:
            return "مقبول، يحتاج تأهيل ومزيد من التحسين، يتحول مباشرة للتأهيل"
        else:
            return "النطاق غير محدد في التعليمات"

# مثال على استخدام الدالة:
if __name__ == "__main__":
    test_scores = [35, 55, 75]
    for score in test_scores:
        action = get_evaluation_action(score)
        print(f"النتيجة: {score}% → الإجراء: {action}")
