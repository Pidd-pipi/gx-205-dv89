from django.conf import settings
from django.db import models


class LogicQuestion(models.Model):
    QUESTION_TYPES = [
        ("number", "数字推理"),
        ("figure", "图形推理"),
        ("logic", "逻辑判断"),
        ("analogy", "类比推理"),
        ("deduction", "演绎推理"),
    ]

    title = models.CharField(max_length=120)
    question_type = models.CharField(max_length=32, choices=QUESTION_TYPES)
    difficulty = models.CharField(max_length=16)
    stem = models.TextField()
    answer = models.CharField(max_length=32)
    explanation = models.TextField()
    knowledge = models.CharField(max_length=120)
    image = models.ImageField(upload_to="questions/", blank=True)

    def __str__(self) -> str:
        return self.title


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    tier = models.CharField(max_length=16, default="青铜")
    demotion_protected = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user_id}:{self.tier}"


class TypeStat(models.Model):
    """按题型累计的答题数与正确数，雷达图和总正确率都从这里取数。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="type_stats"
    )
    question_type = models.CharField(max_length=32)
    answered = models.PositiveIntegerField(default=0)
    correct = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "question_type")


class ExamRecord(models.Model):
    """每次交卷留一档，段位按最近五套的总正确率结算。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_records"
    )
    total = models.PositiveIntegerField()
    correct = models.PositiveIntegerField()
    accuracy = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")


class WrongBookEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(LogicQuestion, on_delete=models.CASCADE)
    mistakes = models.PositiveIntegerField(default=1)
    favorited = models.BooleanField(default=False)
    last_practiced_at = models.DateField(auto_now=True)

    class Meta:
        unique_together = ("user", "question")
