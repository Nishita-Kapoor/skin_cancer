import pandas
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from data.dataloader import *
from data.data_analysis import class_mapping
from glob import glob


def predict(args, device, model):

    path = args.image_path

    all_image_path = glob(os.path.join(args.path, '*', '*.jpg'))
    norm_mean, norm_std = compute_img_mean_std(all_image_path)
    # norm_mean = [0.7630401, 0.5456478, 0.57004625]   # pre-calculated mean and std
    # norm_std = [0.1409284, 0.1526128, 0.16997087]
    image_transforms = image_transform(norm_mean, norm_std)

    loader = image_transforms['test']  # apply 'test' set transforms to image

    image = loader(Image.open(path)).float().unsqueeze(0).to(device)

    # check if checkpoint available and load
    checkpoint_path = "./output/checkpoints/checkpoint_v" + str(args.version) + ".pth"
    if os.path.exists(checkpoint_path):
        checkpoint = load_checkpoint(path=checkpoint_path, model=model)
    else:
        raise AssertionError("Checkpoint doesn't exist, please train model first")

    model = checkpoint["model"]
    model = model.to(device)
    model.eval()

    # Get model prediction
    output = model(image)
    pred = output.max(1, keepdim=True)[1]

    # Check prediction class
    image_prediction = str(class_mapping[int(pred.cpu().numpy())])
    plt.imshow(Image.open(path))
    plt.title("Prediction: " + str(image_prediction))
    save_path = "./output/prediction/"
    create_folder(save_path)

    plt.savefig(save_path + path.split("/")[-1])


def evaluate(args, device, model):
    _, dataloaders = create_dataloaders(args)
    checkpoint_path = "./output/checkpoints/checkpoint_v" + str(args.version) + ".pth"
    checkpoint = load_checkpoint(path=checkpoint_path, model=model)
    save_path = "./output/metrics/"
    create_folder(save_path)

    fig_save = save_path + "confusion_matrix_v" + str(args.version) + ".png"
    csv_save = save_path + "report_v" + str(args.version) + ".csv"

    model = checkpoint["model"]
    model = model.to(device)

    model.eval()
    y_label = []
    y_predict = []
    with torch.no_grad():
        for i, data in tqdm(enumerate(dataloaders['test'])):
            images, labels = data
            N = images.size(0)
            images = Variable(images).to(device)
            outputs = model(images)
            prediction = outputs.max(1, keepdim=True)[1]
            y_label.extend(labels.cpu().numpy())
            y_predict.extend(np.squeeze(prediction.cpu().numpy().T))

    # compute the confusion matrix
    confusion_mtx = confusion_matrix(y_label, y_predict)
    # plot the confusion matrix
    plot_labels = ['akiec', 'bcc', 'bkl', 'df', 'nv', 'vasc', 'mel']

    plot_confusion_matrix(confusion_mtx, fig_path=fig_save, classes=plot_labels)

    report = classification_report(y_label, y_predict, target_names=plot_labels, output_dict=True)
    report_df = pandas.DataFrame(report).transpose()
    report_df.to_csv(csv_save, index=False)
