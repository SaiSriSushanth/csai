from django.shortcuts import render

# Create your views here.
import openai
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import io
import sys
import json
from django.conf import settings
from .models import CodeSubmission
openai.api_key = settings.OPENAI_API_KEY
from accounts.models import Profile

def index(request):
    return render(request, 'code_assistant/index.html')

@csrf_exempt
def run_code(request):
    """
    Naive approach to execute Python code. 
    Not safe for production. 
    """
    if request.method == 'POST':
        code = request.POST.get('code', '')

        question = request.session.get('current_question', None)
        
        # Prepare a fresh execution environment
        context = {}
        # If there's a question, inject the sample input into the context
        if question:
            context['input_data'] = question.get('sample_input')

        # Redirect stdout to capture code output
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        try:
            exec(code, context)
            output = redirected_output.getvalue()
        except Exception as e:
            output = str(e)
        finally:
            sys.stdout = old_stdout
        
        # CodeSubmission.objects.create(code=code, output=output)
        submission = CodeSubmission(code=code, output=output)
        if request.user.is_authenticated:
            submission.user = request.user
        submission.save()

        # return JsonResponse({'output': output})
        if question:
            expected_output = question.get('sample_output')
            # Convert expected_output to string for comparison (assuming GPT returns JSON values)
            def normalize(text):
                return ''.join(text.split())
            
            normalized_output = normalize(output)
            normalized_expected = normalize(str(expected_output))
            
            is_correct = (normalized_output == normalized_expected)

            result = {
                "output": output,
                "expected_output": expected_output,
                "is_correct": is_correct
            }

            # If the user is authenticated, update their profile points and streak.
            if request.user.is_authenticated:
                # Retrieve the user’s profile.
                profile = Profile.objects.get(user=request.user)
                
                # Determine base points from the question difficulty.
                difficulty = question.get('difficulty', 'easy').lower()
                if difficulty == 'easy':
                    base_points = 1
                    xp_gain = 1
                elif difficulty == 'medium':
                    base_points = 3
                    xp_gain = 2
                elif difficulty == 'hard':
                    base_points = 6
                    xp_gain = 3
                else:
                    base_points = 0
                    xp_gain = 0

                if is_correct:
                    # Increase streak by one.
                    profile.streak += 1
                    # Award points multiplied by the streak. (For example: if streak=2, points = base*2.)
                    awarded = base_points * profile.streak
                    profile.points += awarded

                    # Add XP based on difficulty.
                    profile.xp += xp_gain

                    # Level up if XP is 10 or more.
                    level_ups = 0
                    while profile.xp >= 10:
                        profile.level += 1
                        profile.coins += 10
                        profile.xp -= 10
                        level_ups += 1

                    validation_message = f"✅ Correct! You earned {awarded} points (streak: {profile.streak})."
                else:
                    # Reset streak if incorrect.
                    profile.streak = 0
                    validation_message = "❌ Incorrect! Your streak has been reset."
                profile.save()
                result["validation_message"] = validation_message
                result["total_points"] = profile.points
                result["current_streak"] = profile.streak
                result["level"] = profile.level
                result["coins"] = profile.coins
                result["xp"] = profile.xp

            return JsonResponse(result)
        else:
            return JsonResponse({
                'output': output,
                'message': 'No coding challenge selected. Please fetch a question to enable validation.'
            })
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def assistant_feedback(request):

    if request.method == 'POST':
        code = request.POST.get('code', '')
        if request.user.is_authenticated:
            last_five_submissions = CodeSubmission.objects.filter(user=request.user).order_by('-created_at')[:5]
        else:
            last_five_submissions = CodeSubmission.objects.order_by('-created_at')[:5]
        # last_five_submissions = CodeSubmission.objects.order_by('-created_at')[:5]

        code_snippets_str = ""
        for i, submission in enumerate(last_five_submissions):
            code_snippets_str += f"Submission {i+1} (created {submission.created_at}):\n{submission.code}\n\n"
        
        try:
            instruction = (
            "You are an AI assistant that validates Python code. "
            "If the submitted code is correct, appreciate the candidate with an encouraging message. "
            "If errors are found, provide a detailed analysis and corrections. "
            "Your response must strictly adhere to the following exact format:\n"
            "Error identified: {error}\n"
            "corrected code: {correct code}\n"
            "Level of code: {level of the corrected code}\n"
            "Resources: {resources}\n"
            "Feedback: {feedback}"
            )


            messages = [
                # {"role": "system", "content": "You are an AI assistant that helps analyze and improve code."},
                # {
                #     "role": "user",
                #     "content": (
                #         "Here are the last 5 code submissions. "
                #         "Identify common errors or patterns, and provide suggestions "
                #         "with references to relevant learning resources.\n\n"
                #         f"{code_snippets_str}"
                #     )
                # }
                {"role": "system", "content": instruction},
                {"role": "user", "content": f"Please review the following Python code and provide your analysis:\n\n{code}"}

            ]
            
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            print("openai response", response)
            # assistant_message = response.choices[0].message['content']
            try:
                assistant_message = response['choices'][0]['message']['content']
            except KeyError as e:
                print("Response structure error:", e)
                return JsonResponse({'error': 'Unexpected response from OpenAI'}, status=500)
            
            return JsonResponse({'assistant_response': assistant_message})
        
        except Exception as e:
            print("Error in assistant_feedback:", e)
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def learning_resources(request):
    # Fetch the last 5 submissions for the logged in user, or global if not logged in
    if request.user.is_authenticated:
        last_submissions = CodeSubmission.objects.filter(user=request.user).order_by('-created_at')[:5]
    else:
        last_submissions = CodeSubmission.objects.order_by('-created_at')[:5]

    code_snippets_str = ""
    for i, submission in enumerate(last_submissions):
        code_snippets_str += f"Submission {i+1} (created {submission.created_at}):\n{submission.code}\n\n"

    # Build a prompt that instructs GPT to return a valid JSON response
    prompt = (
        # "Based on the following code submissions, suggest learning resources in the form of YouTube videos. "
        # "Group the recommendations by topic. For each topic, list at least one YouTube video with its title, "
        # "a short description, and the URL link. Ensure the recommendations are relevant to the code topics present. "
        # "Return your answer as a valid JSON object in the following format:\n\n"
        # '{\n  "topics": [\n    {\n      "topic": "Topic Name",\n      "videos": [\n        {\n          "title": "Video Title",\n          "description": "Short description",\n          "url": "https://www.youtube.com/..."\n        }\n      ]\n    }\n  ]\n}\n\n'
        # "Only return the JSON object and nothing else.\n\n"
        # f"{code_snippets_str}"
        "Based on the following code submissions, suggest learning resources in the form of YouTube videos(ignore, don't suggest unavailable videos). "
        "Group the recommendations by topic. For each topic, list at least one YouTube video with its title, "
        "a short description, the URL link, and the thumbnail URL (a valid URL to the video's thumbnail image). "
        "Return your answer as a valid JSON object in the following format:\n\n"
        '{\n  "topics": [\n    {\n      "topic": "Topic Name",\n      "videos": [\n        {\n          "title": "Video Title",\n          "description": "Short description",\n          "url": "https://www.youtube.com/...",\n          "thumbnail": "https://img.youtube.com/..." \n        }\n      ]\n    }\n  ]\n}\n\n'
        "Only return the JSON object and nothing else.\n\n"
        f"{code_snippets_str}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # or "gpt-3.5-turbo" if needed
            messages=[
                {"role": "system", "content": "You are an AI assistant that provides educational resource recommendations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        resources_text = response['choices'][0]['message']['content']

        # Try to parse the GPT response as JSON
        try:
            resources_json = json.loads(resources_text)
        except Exception as json_error:
            # In case parsing fails, return an error along with the raw text for debugging
            resources_json = {"error": "Failed to parse GPT response as JSON.", "raw": resources_text}
    except Exception as e:
        resources_json = {"error": str(e)}

    return render(request, 'code_assistant/learning_resources.html', {'resources': resources_json})

@csrf_exempt
def get_question(request):
    """
    Accepts a difficulty (easy, medium, hard) from the POST data and uses GPT to generate a
    LeetCode-style coding challenge. The challenge is returned as a JSON object and also stored
    in the session for later use in solution validation.
    """
    if request.method == 'POST':
        difficulty = request.POST.get('difficulty', '').lower()
        if difficulty not in ['easy', 'medium', 'hard']:
            return JsonResponse({'error': 'Invalid difficulty selected.'}, status=400)

        # Construct a prompt that instructs GPT to generate a LeetCode-style question.
        prompt = (
            f"Generate a LeetCode style coding challenge of {difficulty} difficulty. "
            "The question should include a title, a description, a sample input, and an expected output. "
            "Return your answer as a valid JSON object in the following format:\n\n"
            '{\n'
            '  "title": "Question Title",\n'
            '  "description": "A detailed description of the problem",\n'
            '  "sample_input": <sample input in JSON format>,\n'
            '  "sample_output": <expected output in JSON format>\n'
            '}\n\n'
            "Only return the JSON object and nothing else."
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # or "gpt-3.5-turbo" if needed
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates coding challenges similar to LeetCode."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            question_text = response['choices'][0]['message']['content']

            try:
                # Parse GPT response as JSON.
                question = json.loads(question_text)
            except Exception as json_error:
                return JsonResponse({
                    'error': 'Failed to parse GPT response as JSON.',
                    'raw': question_text
                }, status=500)

            # Store the question in the session for later validation.
            request.session['current_question'] = question
            return JsonResponse({'question': question})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

