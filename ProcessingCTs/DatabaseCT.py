import os
import numpy as np
import SimpleITK as Sitk
from ProcessingCTs.ImageCT import ImageCT
from ProcessingCTs.MaskCT import MaskCT


class DatabaseCT:

    @staticmethod
    def windowing(dir_in, dir_out, wl=-600, ww=1500, slope=1, intercept=-1024):
        for item in DatabaseCT.__ct_file_list(dir_in):
            data = ImageCT(dir_in + item).get_image_data()
            data = data * slope - intercept  # slope * data + intercept
            data[data <= (wl - ww / 2)] = wl - ww / 2
            data[data > (wl + ww / 2)] = wl + ww / 2
            Sitk.WriteImage(Sitk.GetImageFromArray(data), dir_out+item)

    @staticmethod
    def grayscale(dir_in, dir_out):
        for item in DatabaseCT.__ct_file_list(dir_in):
            data = ImageCT(dir_in + item).get_image_data()
            min_image_value = np.min(data)
            max_image_value = np.max(data)
            data = (data - min_image_value) * ((255 - 0) / (max_image_value - min_image_value)) + 0
            data = data.astype(np.uint8)
            Sitk.WriteImage(Sitk.GetImageFromArray(data), dir_out+item)

    @staticmethod
    def masking(dir_in, dir_out, mask_dir):
        for filename in DatabaseCT.__ct_file_list(dir_in):
            image = Sitk.ReadImage(dir_in + filename)
            image_mask = Sitk.ReadImage(mask_dir + filename.replace(".nii", "_roi.nii"))
            image_mask = Sitk.GetImageFromArray(Sitk.GetArrayFromImage(image_mask).astype(np.uint8))
            masked_image = Sitk.Mask(image, image_mask, maskingValue=0, outsideValue=0)
            Sitk.WriteImage(masked_image, dir_out + filename)

    @staticmethod
    def cropping_minimum(dir_in, dir_out):
        max_width = DatabaseCT.__find_max_width_per_database(dir_in)
        for item in DatabaseCT.__ct_file_list(dir_in):
            image = ImageCT(dir_in + item)
            cropped_image_data = image.crop_per_ct(max_width)
            Sitk.WriteImage(Sitk.GetImageFromArray(cropped_image_data), dir_out+item)

    @staticmethod
    def create_windowed_masks(dir_in, dir_out, window_width):
        for filename in DatabaseCT.__ct_file_list(dir_in):
            mask_image = MaskCT(dir_in+filename)
            try:
                mask_image.window_mask(window_width)
            except IndexError:
                print("Width is to big for file: ", filename)
                print("File mask is omitted.")
            else:
                mask_image.save_image(dir_out+filename)

    @staticmethod
    def __ct_file_list(filepath):
        file_list = os.listdir(filepath)
        return file_list
        # results = []
        # for filename in file_list:
        #     results.append(filename)
#        return results

    @staticmethod
    def __find_max_width_per_database(dir_in):
        widths = []
        for item in DatabaseCT.__ct_file_list(dir_in):
            image = ImageCT(dir_in + item)
            widths.append(image.find_max_widths_per_ct())
        return max(widths)
