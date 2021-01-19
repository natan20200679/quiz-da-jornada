from django.http import HttpResponse
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.utils.timezone import now

from quiz_devpro.quiz.forms import AlunoForm
from quiz_devpro.quiz.models import Pergunta, Aluno, Resposta


def indice(requisicao):
    if requisicao.method == 'POST':
        email = requisicao.POST['email']
        try:
            aluno = Aluno.objects.get(email=email)
        except Aluno.DoesNotExist:
            form = AlunoForm(requisicao.POST)
        if form.is_valid():
            aluno = form.save()
            requisicao.session['aluno_id'] = aluno.id
            return redirect('/perguntas/1')
        contexto = {'form': form}
        return render(requisicao, 'quiz/indice.html', contexto)
    else:
            requisicao.session['aluno_id'] = Aluno.id
            return redirect('/perguntas/1')

def perguntas(requisicao, indice):
    aluno_id = requisicao.session['aluno_id']
    try:
        pergunta = Pergunta.objects.filter(disponivel=True).order_by('id')[indice - 1]
    except IndexError:
        return redirect('/classificacao')
    else:
        contexto = {'indice': indice, 'pergunta': pergunta}
        if requisicao.method == 'POST':
            alternativa_escolhida = int(requisicao.POST['alternativa'])

            if alternativa_escolhida == pergunta.alternativa_correta:
                # Guardar resposta e calcular pontos
                # 100 pontos para quem responder primeiro
                # Quem responde depois, perde um ponto por segundo de diferença
                # Até chegar em 1 ponto
                try:
                    primeira_resposta = Resposta.objects.filter(pergunta=pergunta).order_by('criacao')[0]
                except IndexError:
                    pontos = 100
                else:
                    tempo_primeira_resposta = primeira_resposta.criacao
                    diferenca = now() - tempo_primeira_resposta
                    pontos = 100 - int(diferenca.total_seconds())
                    pontos = max(pontos, 1)

                Resposta(aluno_id=aluno_id, pergunta=pergunta, pontos=pontos).save()
                return redirect(f'/perguntas/{indice + 1}')
            contexto['alternativa_escolhida'] = alternativa_escolhida

        return render(requisicao, 'quiz/pergunta.html', contexto)

def classificacao(requisicao):
    aluno_id = requisicao.session['aluno_id']
    dct = Resposta.objects.filter(aluno_id=aluno_id).aggregate(Sum('pontos'))
    pontos_aluno = dct['pontos__sum']
    alunos_pontuacao_maior = Resposta.objects.values('aluno').annotate(Sum('pontos')).filter\
        (pontos__sum__gt=pontos_aluno).count()
    primeiros_5_alunos = Resposta.objects.values('aluno', 'aluno__nome').annotate(Sum('pontos')).filter \
        (pontos__sum__gt=pontos_aluno).order('-pontos__sum')[:5]
    primeiros_5_alunos = list(primeiros_5_alunos)
    contexto = {'pontos': pontos_aluno,
                'posicao': alunos_pontuacao_maior + 1,
                'primeiros_5_alunos': primeiros_5_alunos
                }
    return render(requisicao, 'quiz/classificacao.html')
