import time
import json
from itertools import product

import torch
from models.fairgraph.method import run
from models.fairgraph.dataset import POKEC, NBA, Citeseer
from utils import set_seed, parse_arguments, create_writer

# Parse command line arguments
args, adjusted_args = parse_arguments()

datasets = {
    'pokec':POKEC,
    'nba':NBA,
    'citeseer':Citeseer
}

MODEL = 'LPGraphair' if args.lp else 'Graphair'

# Train and evaluate
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print('running inference with the following args:\n')
for arg, value in vars(args).items():
    print(f"{arg}: {value}")

hyperparameters = {
    'alpha': args.alphas,
    'beta': args.betas,
    'gamma': args.gammas,
    'lam': args.lams,
    'lr': args.lr,
    'model_lr': args.model_lr,
    'hidden': args.hidden
}

writer = create_writer(args.dataset, MODEL, args.epochs, hyperparameters)

unique_id = time.strftime("%Y%m%d%H%M")
filename = f"results_{unique_id}_{args.dataset}_epoch={args.epochs}_"
for arg, value in adjusted_args.items():
    filename += f"{arg}_{value}_"
filename += ".json"

# with open(f'results/{filename}', 'w', encoding='utf-8') as f:
#     print('running inference with the following args:\n')
#     for arg, value in vars(args).items():
#         print(f"{arg}: {value}")
#     json.dump({'using following arguments for model train and inference':vars(args)}, f, indent=4)

print(hyperparameters.values())

for idx, params in enumerate(product(*hyperparameters.values())):
    set_seed(20)
    alpha, beta, gamma, lam, lr, model_lr, hidden = params

    if 'pokec' in args.dataset:
        dataset = datasets['pokec'](dataset_sample=args.dataset)
    else:
        dataset = datasets[args.dataset]()
    run_fairgraph = run()
    print(f'running with params: alpha = {alpha}, beta = {beta}, gamma = {gamma}, '
            f'lamda = {lam}, lr = {lr}, model lr = {model_lr}, hidden_size = {hidden}')
    results = run_fairgraph.run(device, dataset=dataset, model=MODEL,
                                epochs=args.epochs, test_epochs=args.test_epochs,
                                batch_size=1000, lr=lr, model_lr=model_lr, weight_decay=args.wd,
                                hidden=hidden, alpha=alpha, beta=beta, gamma=gamma, lam=lam)

    hparams = {
            'alpha': alpha,
            'beta': beta,
            'gamma': gamma,
            'lam': lam,
            'lr': lr,
            'model_lr': model_lr,
            'hidden': hidden,
            'dataset':args.dataset,
            'model':MODEL,
            'test_epochs':args.test_epochs
            }

    metrics = {metric: value[0] for metric, value in results.items() if metric not in ['homophily', 'spearman']}
    results = {metric: value for metric, value in results.items() if metric not in ['homophily', 'spearman']}
    writer.add_hparams(hparams, metrics)

    with open(f'results/{filename}', 'r+', encoding='utf-8') as f:
        data = json.load(f)
        data[f'run_{idx + 1}'] = {'hyperparameters':hparams, 'results':results}
        f.seek(0)  # Move the cursor to the beginning of the file
        json.dump(data, f, indent=4)
        f.truncate()
        f.flush()

writer.close()
