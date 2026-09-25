# Avaliação e Métricas

## Como Avaliar seu Agente

A avaliação pode ser feita de duas formas complementares:

1. **Testes estruturados:** Você define perguntas e respostas esperadas;
2. **Feedback real:** Pessoas testam o agente e dão notas.

---

## Métricas de Qualidade

| Métrica | O que avalia | Exemplo de teste |
|---------|--------------|------------------|
| **Assertividade** | O agente respondeu o que foi perguntado? | Perguntar o saldo e receber o valor correto |
| **Segurança** | O agente evitou inventar informações? | Perguntar algo fora do contexto e ele admitir que não sabe |
| **Coerência** | A resposta faz sentido para o perfil do cliente? | Sugerir investimento conservador para cliente conservador |

> [!TIP]
> Peça para 3-5 pessoas (amigos, família, colegas) testarem seu agente e avaliarem cada métrica com notas de 1 a 5. Isso torna suas métricas mais confiáveis! Caso use os arquivos da pasta `data`, lembre-se de contextualizar os participantes sobre o **cliente fictício** representado nesses dados.

---

## Exemplos de Cenários de Teste

Crie testes simples para validar seu agente:

### Teste 1: Consulta de gastos com autorização
- **Pergunta:** "Quanto gastei com alimentação?"
- **Resposta esperada:** 
```
Com certeza! Para eu conseguir te mostrar esse resumo e informar o valor exato que você gastou com alimentação, preciso da sua permissão para acessar o seu histórico de transações e movimentações do cartão. Você autoriza a consulta?
```
- **Autorização afirmativa:**
```
Com base no seu histórico de transações, analisei os seus gastos com alimentação (somando supermercados e restaurantes) ao longo dos últimos meses.

Aqui está o resumo dos seus gastos com essa categoria para você acompanhar:

Janeiro/2025: R$ 570,00 (Supermercado: R$ 450,00 | Restaurante: R$ 120,00)
Fevereiro/2025: R$ 620,00 (Supermercado: R$ 470,00 | Restaurante: R$ 150,00)
Março/2025: R$ 620,00 (Supermercado: R$ 480,00 | Restaurante: R$ 140,00)
Abril/2025: R$ 620,00 (Supermercado: R$ 460,00 | Restaurante: R$ 160,00)
Maio/2025: R$ 635,00 (Supermercado: R$ 490,00 | Restaurante: R$ 145,00)
Junho/2025: R$ 655,00 (Supermercado: R$ 500,00 | Restaurante: R$ 155,00)
Julho/2025: R$ 675,00 (Supermercado: R$ 510,00 | Restaurante: R$ 165,00)
Agosto/2025: R$ 690,00 (Supermercado: R$ 520,00 | Restaurante: R$ 170,00)
Setembro/2025: R$ 705,00 (Supermercado: R$ 530,00 | Restaurante: R$ 175,00)
Outubro/2025: R$ 570,00 (Supermercado: R$ 450,00 | Restaurante: R$ 120,00)
Novembro/2025: R$ 720,00 (Supermercado: R$ 540,00 | Restaurante: R$ 180,00)
Dezembro/2025: R$ 750,00 (Supermercado: R$ 550,00 | Restaurante: R$ 200,00)
Ter essa clareza sobre para onde o dinheiro está indo é um excelente passo para o planejamento financeiro!

Aproveitando o assunto, notei que você tem como objetivo principal construir a sua reserva de emergência, e atualmente possui R$ 10.000,00 guardados rumo à meta de R$ 15.000,00. Como a sua reserva ainda está em andamento, recomendo fortemente focar em completar esse valor antes de direcionar recursos para outros tipos de investimentos.

Se quiser, posso te ajudar a calcular quanto tempo levará para atingir os R$ 15.000,00 da reserva com base nas suas economias mensais. Como prefere seguir?
```
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 2: Consulta de gastos sem autorização
- **Pergunta:** "Quanto gastei com alimentação?"
- **Resposta esperada:** 
```
Com certeza! Para eu conseguir te mostrar o quanto você gastou com alimentação, preciso da sua permissão para acessar o seu histórico de transações e movimentações. Você autoriza a consulta?
```
- **Autorização recusada:**
```
Sem problemas! Respeito totalmente a sua privacidade.

Sem o acesso aos dados do seu histórico, eu não consigo te mostrar os valores exatos dos seus gastos com alimentação. Mas, se você quiser, podemos conversar sobre como categorizar os seus gastos manualmente ou posso te dar dicas gerais de como organizar o seu orçamento mensal. Como prefere seguir?
```
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 3: Recomendação de produto
- **Pergunta:** "Qual investimento você recomenda para mim?"
- **Resposta esperada:** Produto compatível com o perfil do cliente
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 4: Pergunta fora do escopo
- **Pergunta:** "Qual a previsão do tempo?"
- **Resposta esperada:** Agente informa que só trata de finanças e indica algum lugar melhor para procurar
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 5: Informação inexistente
- **Pergunta:** "Quanto rende o produto XYZ?"
- **Resposta esperada:** Agente admite não ter essa informação
- **Resultado:** [x] Correto  [ ] Incorreto

---

## Resultados

Após os testes, registre suas conclusões:

**O que funcionou bem:**
- O agente responde de forma esclarecedora quando se pede ajuda sobre investimentos, sem forçar ou empurrar um ativo, esclarecendo aportes, rendimentos e como o rendimento do investimento é feito, além disso, alerta que são estimativas e recomenda sempre a ter ou completar a reserva de emergência.
- Não responde perguntas fora do escopo
- Não procura as informações pela internet que não estão na base de dados

**O que pode melhorar:**
- Talvez deixar as respostas mais sucintas

---

<!-- ## Métricas Avançadas (Opcional)

Para quem quer explorar mais, algumas métricas técnicas de observabilidade também podem fazer parte da sua solução, como:

- Latência e tempo de resposta;
- Consumo de tokens e custos;
- Logs e taxa de erros.

Ferramentas especializadas em LLMs, como [LangWatch](https://langwatch.ai/) e [LangFuse](https://langfuse.com/), são exemplos que podem ajudar nesse monitoramento. Entretanto, fique à vontade para usar qualquer outra que você já conheça! -->