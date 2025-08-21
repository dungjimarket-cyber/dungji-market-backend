from django import forms;
from django.contrib.auth.forms import ReadOnlyPasswordHashField;
from .models import User;

class UserCreationForm(forms.ModelForm):
  """
  관리자에서 User 생성 시 사용하는 폼 (비밀번호 암호화 지원)
  """
  password1 = forms.CharField(label='비밀번호', widget=forms.PasswordInput, required=True, help_text='필수 입력')
  password2 = forms.CharField(label='비밀번호 확인', widget=forms.PasswordInput, required=True, help_text='필수 입력')

  class Meta:
    model = User;
    fields = ('username', 'email', 'role');
    labels = {
      'username': '아이디',  # 사용자 이름 → 아이디로 변경
    }
    widgets = {
      'username': forms.TextInput(attrs={'required': True}),
      'email': forms.EmailInput(attrs={'required': True}),
      'role': forms.Select(attrs={'required': True}),
    }
    help_texts = {
      'username': '필수 입력',
      'email': '필수 입력',
      'role': '필수 입력',
    }

  def clean_password2(self):
    password1 = self.cleaned_data.get('password1');
    password2 = self.cleaned_data.get('password2');
    if password1 and password2 and password1 != password2:
      raise forms.ValidationError('비밀번호가 일치하지 않습니다.');
    return password2;

  def save(self, commit=True):
    user = super().save(commit=False);
    user.set_password(self.cleaned_data['password1']);
    if commit:
      user.save();
    return user;

class UserChangeForm(forms.ModelForm):
  """
  관리자에서 User 수정 시 사용하는 폼
  """
  password = ReadOnlyPasswordHashField(label='비밀번호', help_text='비밀번호는 <a href="../password/">이 폼</a>을 통해 변경하세요.');

  class Meta:
    model = User;
    fields = ('username', 'email', 'role', 'password', 'is_active', 'is_staff');
    labels = {
      'username': '아이디',  # 사용자 이름 → 아이디로 변경
    }
