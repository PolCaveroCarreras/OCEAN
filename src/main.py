import torch
from torch.utils.data import DataLoader
from dataset import BlueFinLib
from ResNet import ResNet50, ResNet101, ResNet152
import torch.optim as optim
from torchvision import transforms
from sklearn.metrics import confusion_matrix
import torch.nn.functional as F
import numpy as np
from tqdm import tqdm


device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

def accuracy(labels: torch.Tensor, outputs: torch.Tensor) -> int:
    '''
    This function returns the number of coincidences that happen in two arrays of the same length.

    Arguments:
    ----------
    labels : torch.Tensor [batch, num_classes]
        The ground truth of the classes.
    outputs : torch.Tensor [batch, num_classes]
        The model prediction of the most likely class.
    
    Returns:
    --------
    acum : int
        The number of coincidences.
    '''
    preds = outputs.argmax(-1, keepdim=True)
    labels = labels.argmax(-1, keepdim=True) # bc we have done one_hot encoding.
    # label shape [batch, 1], outputs shape [batch, 1]
    acum = preds.eq(labels.view_as(preds)).sum().item() # sums the times both arrays coincide.
    return acum

def train_single_epoch(model, train_loader, optimizer):
    model.train()
    accs, losses = [], []
    for x, y in tqdm(train_loader, unit="batch", total=len(train_loader)):
        optimizer.zero_grad()
        x, y = x.to(device), y.to(device)
        y_ = model(x)
        loss = F.cross_entropy(y_, y)
        loss.backward()
        optimizer.step()
        acc = accuracy(y, y_)
        losses.append(loss.item())
        accs.append(acc) # accs.append(acc.item())
    return np.mean(losses), np.sum(accs)/len(train_loader.dataset)


def eval_single_epoch(model, val_loader):
    '''
    This function is made for both validation and test.
    '''
    accs, losses = [], []
    with torch.no_grad():
        model.eval()
        for x, y in val_loader:
            x, y = x.to(device), y.to(device)
            y_ = model(x)
            loss = F.cross_entropy(y_, y)
            acc = accuracy(y, y_)
            losses.append(loss.item())
            accs.append(acc) # accs.append(acc.item())
            pred = y_.detach().numpy()
            cm = confusion_matrix(y.argmax(-1), pred.argmax(-1))
            print('Confussion matrix eval:\n', cm) # maybe not necessary to be print every time.
    return  np.mean(losses), np.sum(accs)/len(val_loader.dataset)

def data_loaders(config):
    data_transforms = transforms.Compose([transforms.ToTensor(), transforms.Normalize(0.5, 0.5)])
    total_data = BlueFinLib(pickle_path = "/home/usuaris/veussd/DATABASES/Ocean/toyDataset.pkl", 
                            img_dir = "/home/usuaris/veussd/DATABASES/Ocean/Spectrograms_AcousticTrends/23_05_21_12_08_09_23hqmc53_zany-totem-48", 
                            config = config,
                            transform=data_transforms)
    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(total_data,
                                                                              [config['num_samples_train'],
                                                                                config['num_samples_val'],
                                                                                config['num_samples_test']])
    train_loader = DataLoader(train_dataset, batch_size=config["batch_size"], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config["batch_size"])
    test_loader = DataLoader(test_dataset, batch_size=config["batch_size"])

    return train_loader, val_loader, test_loader

def train_model(config):

    train_loader, val_loader, test_loader = data_loaders(config)

    my_model = ResNet50(2, 1).to(device)
    optimizer = optim.Adam(my_model.parameters(), config["lr"])

    # TRAINING
    for epoch in range(config["epochs"]):
        loss, acc = train_single_epoch(my_model, train_loader, optimizer)
        print(f"Train Epoch {epoch} loss={loss:.2f} acc={acc:.2f}")
        loss, acc = eval_single_epoch(my_model, val_loader)
        print(f"Eval Epoch {epoch} loss={loss:.2f} acc={acc:.2f}")
    
    # TEST
    loss, acc = eval_single_epoch(my_model, test_loader)
    print(f"Test loss={loss:.2f} acc={acc:.2f}")

    return my_model

if __name__ == "__main__":
    # TODO: calculate properly "random_crop_frames". Use the fede function
    
    config = {
        "lr": 1e-3,
        "batch_size": 3, # This number must be bigger than one (nn.BatchNorm)
        "epochs": 2,
        "num_samples_train": 3,
        "num_samples_val": 2,
        "num_samples_test": 2,
        "random_crop_frames": 4,
    }
    my_model = train_model(config)
