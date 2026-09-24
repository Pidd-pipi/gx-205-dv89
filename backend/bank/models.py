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


class WrongBookEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(LogicQuestion, on_delete=models.CASCADE)
    mistakes = models.PositiveIntegerField(default=1)
    favorited = models.BooleanField(default=False)
    last_practiced_at = models.DateField(auto_now=True)

    class Meta:
        unique_together = ("user", "question")


class TypeStat(models.Model):
    """按题型累计的答题数与正确数。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question_type = models.CharField(max_length=32)
    answered = models.PositiveIntegerField(default=0)
    correct = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "question_type")


class ExamRecord(models.Model):
    """一次交卷的总题数与正确数，用于最近五套练习的段位结算。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total = models.PositiveIntegerField()
    correct = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class UserProgress(models.Model):
    """账号当前段位与掉段保护状态。"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tier = models.CharField(max_length=16, default="青铜")
    shield_available = models.BooleanField(default=True)
